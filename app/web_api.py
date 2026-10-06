"""Frontend-shaped API under /web: returns exactly the shapes in web/src/lib/types.ts,
one endpoint per callback in web/src/sample/routes.tsx.

  Solicitor   GET  /web/cases                      -> CaseWithDocuments[]
              POST /web/cases                      {applicantName, otherPartyName, caseType, askLabel} -> CaseWithDocuments (with a client link)
              POST /web/cases/from-letter          multipart files[] -> {case, documents, documentId}   (drop a letter to start a case)
              GET  /web/cases/{id}                 -> CaseWithDocuments
              PATCH /web/cases/{id}                {otherPartyName?, askLabel?, applicantName?, caseType?} -> CaseWithDocuments (re-checks every letter)
              PUT  /web/cases/{id}/selection       {documentIds} -> Case
              POST /web/cases/{id}/documents       multipart files[] (pages of one letter), replaces? -> CaseDocument (result null while checking)
              GET  /web/cases/{id}/documents/{doc} -> CaseDocument (poll until result is set)
              POST /web/cases/{id}/client-link     -> Case   DELETE -> Case
              POST /web/cases/{id}/submit          {documentIds, reason} -> {case, documents, summary, filename, submissionId}
                                                   (freezes the pack and schedules the LAA's independent check; case.submissionId is
                                                   set from here on, and the pack is GET /web/submissions/{submissionId}/pack.zip)
  Client      GET  /web/client/{token}             -> {firstName, firmName, askLabel, linkExpiresAt, latestDocument, state}
              POST /web/client/{token}/upload      multipart files[] -> {documentId}
              GET  /web/client/{token}/documents/{doc} -> {document, state}
              Client documents are the reduced shape: no text, quotes, reasoning, flags, names or verification.
  Caseworker  GET  /web/queue                      -> CaseWithDocuments[] (one per undecided submission, from its frozen snapshot;
                                                   case.ref is the LAA reference, case.submissionId and case.laaCheck are set)
              GET  /web/queue/{id}                 -> CaseWithDocuments ({id} = submission id, LAA ref, or case id -> its latest submission)
              POST /web/queue/{id}/decision        {action, note, submissionId?} -> Decision (acts on that submission, else the latest submitted)
              GET  /web/submissions/{id}/pack.zip  -> the submitted files (or their text) plus verification-summary.txt
              POST /web/inbox                      multipart email, files[] -> {email, firm, documents, reply}
  Files       GET  /web/documents/{doc}/file/{page} -> the uploaded file while it is still held in memory
"""
from __future__ import annotations

import time
import io
import re
import zipfile
from pathlib import PurePath

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app import core, webmap
from app.core import store
from engine.ingest import UnsupportedFile, ingest

router = APIRouter(prefix="/web", tags=["frontend"])


# --------------------------------------------------------------------------- #
class NewCase(BaseModel):
    applicantName: str = ""
    otherPartyName: str = ""
    caseType: str = "Child arrangements"
    askLabel: str = "Letter from your support worker"
    firm: str | None = None
    applicationDate: str | None = Field(default=None, description="ISO date; defaults to today (the application is being made now)")


class CaseUpdate(BaseModel):
    applicantName: str | None = None
    otherPartyName: str | None = None
    caseType: str | None = None
    askLabel: str | None = None


class Selection(BaseModel):
    documentIds: list[str]


class Submit(BaseModel):
    documentIds: list[str]
    reason: str | None = None


class DecisionIn(BaseModel):
    action: str = Field(pattern="^(accept|return|refer)$")
    note: str = ""
    caseworker: str = "caseworker"
    submissionId: str | None = None  # exactly this submission; otherwise the case's latest submitted one


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def _case(case_id: str) -> dict:
    c = store.get_case(case_id)
    if not c:
        raise HTTPException(404, "case not found")
    return c


def _base(request: Request) -> str:
    """Origin for the file links the pages carry. Behind a TLS-terminating proxy the app sees
    plain http; a browser on the https page would refuse that (mixed content), so the forwarded
    scheme wins when the proxy sends one."""
    base = request.base_url
    proto = request.headers.get("x-forwarded-proto")
    if proto in ("http", "https") and proto != base.scheme:
        base = base.replace(scheme=proto)
    return str(base).rstrip("/")


async def _ingest_files(files: list[UploadFile]) -> tuple[str, bool, list[tuple[bytes, str]], list[dict]]:
    """Several files are the pages of one letter. Returns text, needs_transcription, held files, pages."""
    texts, held, pages, needs = [], [], [], False
    for f in files:
        data = await f.read()
        name = f.filename or "upload"
        try:
            ing = ingest(data, name)
        except UnsupportedFile as e:
            raise HTTPException(415, str(e))
        if ing.text.strip():
            texts.append(ing.text)
        needs = needs or ing.needs_transcription
        blob = ing.data or data
        media = ing.media_type or webmap.content_type(name)
        held.append((blob, media))
        shown = name if blob is data else f"{PurePath(name).stem}.jpg"
        pages.append({"filename": shown, "contentType": media if blob is not data else webmap.content_type(name)})
    return "\n\n".join(texts), needs, held, pages


def _add_document(case: dict, uploaded_by: str, text: str, needs: bool, held: list, pages: list[dict],
                  replaces: str | None, background: BackgroundTasks) -> dict:
    doc = store.add_document(case["id"], pages[0]["filename"], uploaded_by, None, held[0][0] if held else None, text, replaces, pages=pages)
    store.set_files(doc["id"], held)
    background.add_task(core.run_check, case, doc, text, needs, held if needs else None)
    return doc


# --------------------------------------------------------------------------- #
# solicitor
# --------------------------------------------------------------------------- #
@router.get("/cases")
def list_cases(request: Request):
    return [webmap.case_with_documents(store, c, base_url=_base(request)) for c in store.list_cases()]


@router.post("/cases", status_code=201)
def create_case(body: NewCase, request: Request):
    c = store.create_case(body.applicantName, body.otherPartyName or None, body.caseType, "provider", work_type="licensed",
                          firm_name=body.firm or "Demo Family Law LLP", ask_label=body.askLabel, application_date=body.applicationDate or _today())
    store.create_client_link(c["id"], 7)
    return webmap.case_with_documents(store, c, base_url=_base(request))


@router.post("/cases/from-letter", status_code=201)
async def case_from_letter(request: Request, background: BackgroundTasks, files: list[UploadFile] = File(...), firm: str | None = Form(None)):
    text, needs, held, pages = await _ingest_files(files)
    c = store.create_case("", None, "Child arrangements", "provider", work_type="licensed", firm_name=firm or "Demo Family Law LLP",
                          ask_label="Letter from your support worker", application_date=_today())
    doc = _add_document(c, "provider", text, needs, held, pages, None, background)
    out = webmap.case_with_documents(store, c, base_url=_base(request))
    out["documentId"] = doc["id"]
    return out


@router.get("/cases/{case_id}")
def get_case(case_id: str, request: Request):
    return webmap.case_with_documents(store, _case(case_id), base_url=_base(request))


@router.patch("/cases/{case_id}")
async def update_case(case_id: str, body: CaseUpdate, request: Request, background: BackgroundTasks):
    c = _case(case_id)
    fields = {k: v for k, v in {"applicant_name": body.applicantName, "other_party_name": body.otherPartyName,
                                "case_type": body.caseType, "ask_label": body.askLabel}.items() if v is not None}
    c = store.update_case(c["id"], **fields)
    store.audit("provider", "case.update", c["id"], fields)
    if "applicant_name" in fields or "other_party_name" in fields:
        background.add_task(core.recheck_case, c)  # "Changing it checks every letter again"
    return webmap.case_with_documents(store, c, base_url=_base(request))


@router.put("/cases/{case_id}/selection")
def set_selection(case_id: str, body: Selection, request: Request):
    c = store.set_selection(_case(case_id)["id"], body.documentIds, "provider")
    return webmap.case_with_documents(store, c, base_url=_base(request))["case"]


@router.post("/cases/{case_id}/documents", status_code=202)
async def add_document(case_id: str, request: Request, background: BackgroundTasks, files: list[UploadFile] = File(...),
                       replaces: str | None = Form(None), uploadedBy: str = Form("provider")):
    c = _case(case_id)
    text, needs, held, pages = await _ingest_files(files)
    doc = _add_document(c, uploadedBy, text, needs, held, pages, replaces, background)
    return webmap.to_document(store, doc, _base(request))


@router.get("/cases/{case_id}/documents/{document_id}")
def get_document(case_id: str, document_id: str, request: Request):
    c = _case(case_id)
    d = store.get_document(document_id)
    if not d or d["case_id"] != c["id"]:
        raise HTTPException(404, "document not found")
    return webmap.to_document(store, d, _base(request))


@router.post("/cases/{case_id}/client-link", status_code=201)
def client_link(case_id: str, request: Request):
    c = _case(case_id)
    store.revoke_client_links(c["id"])
    store.create_client_link(c["id"], 7)
    store.audit("provider", "client_link.create", c["id"])
    return webmap.case_with_documents(store, c, base_url=_base(request))["case"]


@router.delete("/cases/{case_id}/client-link")
def revoke_client_link(case_id: str, request: Request):
    c = _case(case_id)
    store.revoke_client_links(c["id"])
    store.audit("provider", "client_link.revoke", c["id"])
    return webmap.case_with_documents(store, c, base_url=_base(request))["case"]


@router.post("/cases/{case_id}/submit", status_code=201)
def submit(case_id: str, body: Submit, request: Request, background: BackgroundTasks):
    c = _case(case_id)
    docs = [store.get_document(d) for d in body.documentIds]
    docs = [d for d in docs if d and d["case_id"] == c["id"]]
    if not docs:
        raise HTTPException(400, "choose at least one document")
    if any(d["status"] == "checking" for d in docs):
        raise HTTPException(409, "a chosen document is still being checked")
    sub = store.create_submission(c["id"], [d["id"] for d in docs], None, body.reason, "provider")
    background.add_task(core.laa_check, sub)  # link 2: the LAA re-checks the frozen pack independently
    out = webmap.case_with_documents(store, c, only_ids=[d["id"] for d in docs], base_url=_base(request))
    out["summary"] = webmap.verification_summary(out["case"], out["documents"])
    out["filename"] = f"Gateway Check {c['ref']}.txt"
    out["submissionId"] = sub["id"]
    return out


# --------------------------------------------------------------------------- #
# client
# --------------------------------------------------------------------------- #
# A client code is eight characters (about 40 bits) so it can be read out over the phone.
# That is only safe if nobody can try codes quickly: after this many misses from one
# address within the window, further attempts from it are refused for the rest of the window.
_MISS_LIMIT, _MISS_WINDOW_S = 20, 15 * 60
_misses: dict[str, list[float]] = {}
# The address can be forged by whoever can set X-Forwarded-For, so a second, address-independent
# budget caps guessing outright: this many misses in the window from everyone together.
_MISS_LIMIT_ALL = 200
_ALL = "*"


def _client_case(token: str, request: Request | None = None) -> dict:
    host = (request.client.host if request and request.client else None) or "unknown"
    cutoff = time.time() - _MISS_WINDOW_S
    recent = [t for t in _misses.get(host, []) if t > cutoff]
    recent_all = [t for t in _misses.get(_ALL, []) if t > cutoff]
    _misses[host], _misses[_ALL] = recent, recent_all
    if len(recent) >= _MISS_LIMIT or len(recent_all) >= _MISS_LIMIT_ALL:
        raise HTTPException(429, "too many attempts; try again later")
    link = store.resolve_client_link(token)
    if not link:
        _misses[host], _misses[_ALL] = recent + [time.time()], recent_all + [time.time()]
        store.audit("client", "client_link.miss", host, {"attempts": len(recent) + 1})
        raise HTTPException(404, "link not found or expired")
    if recent:
        _misses.pop(host, None)
    return store.get_case(link["case_id"])


@router.get("/client/{token}")
def client_view(token: str, request: Request):
    """Applicant view: first name, plain messages, the reduced document shape. No legal reasoning, no LAA detail."""
    c = _client_case(token, request)
    link = store.latest_client_link(c["id"])
    docs = [webmap.to_document(store, d, _base(request), role="client") for d in store.list_documents(c["id"]) if d["uploaded_by"] == "client"]
    latest = docs[-1] if docs else None
    return {"firstName": c.get("applicant_first_name") or "", "firmName": webmap.firm_short(c.get("firm_name")),
            "askLabel": c.get("ask_label") or "", "linkExpiresAt": link["expires_at"] if link else None,
            "latestDocument": latest, "state": webmap.client_state(latest["result"]) if latest else None}


@router.post("/client/{token}/upload", status_code=202)
async def client_upload(token: str, background: BackgroundTasks, files: list[UploadFile] = File(...)):
    c = _client_case(token)
    text, needs, held, pages = await _ingest_files(files)
    doc = _add_document(c, "client", text, needs, held, pages, None, background)
    return {"documentId": doc["id"], "pages": len(pages)}


@router.get("/client/{token}/documents/{document_id}")
def client_document(token: str, document_id: str, request: Request):
    c = _client_case(token, request)
    d = store.get_document(document_id)
    if not d or d["case_id"] != c["id"]:
        raise HTTPException(404, "document not found")
    doc = webmap.to_document(store, d, _base(request), role="client")
    return {"document": doc, "state": webmap.client_state(doc["result"])}


# --------------------------------------------------------------------------- #
# caseworker: everything here comes from the frozen submission snapshot (link 2),
# never from the live case, so a later re-check, name change or purge cannot
# change what the caseworker sees or decides on.
# --------------------------------------------------------------------------- #
def _submission(ident: str) -> dict:
    """{ident} is a submission id or LAA reference, else a case id or case ref (its latest submitted
    submission, or failing that its latest one, so a decided case can still be opened)."""
    sub = store.get_submission(ident)
    if sub:
        return sub
    c = store.get_case(ident)
    if c:
        sub = store.latest_submission(c["id"], status="submitted") or store.latest_submission(c["id"])
    if not sub:
        raise HTTPException(404, "no submission for that case")
    return sub


def _queue_items(request: Request) -> list[dict]:
    """One row per undecided submission, each from its own snapshot and carrying its submissionId."""
    return [webmap.submission_with_documents(store, s, "caseworker", base_url=_base(request))
            for s in store.list_submissions() if s["status"] == "submitted"]


@router.get("/queue")
def queue(request: Request):
    return _queue_items(request)


@router.get("/queue/{ident}")
def review(ident: str, request: Request):
    return webmap.submission_with_documents(store, _submission(ident), "caseworker", base_url=_base(request))


@router.post("/queue/{ident}/decision", status_code=201)
def decide(ident: str, body: DecisionIn):
    """Decide exactly one submission: body.submissionId if given, else the one {ident} names (a submission id,
    or a case id -> its latest submitted submission)."""
    if body.submissionId:
        sub = store.get_submission(body.submissionId)
        if not sub:
            raise HTTPException(404, "submission not found")
        c = store.get_case(ident)
        if sub["id"] != ident and sub["laa_ref"] != ident and not (c and c["id"] == sub["case_id"]):
            raise HTTPException(409, "that submission belongs to a different case")
    else:
        sub = _submission(ident)
    d = store.add_decision(sub["id"], body.caseworker, body.action, body.note or None)
    return {**webmap.to_decision(d), "submissionId": sub["id"]}


@router.get("/submissions/{ident}/pack.zip")
def submission_pack(ident: str):
    """The pack as the LAA received it: each submitted file (from memory while still held, else the frozen
    text as .txt) plus verification-summary.txt. Built from the snapshot, with the LAA reference."""
    sub = _submission(ident)
    view = webmap.submission_with_documents(store, sub, "caseworker")
    buf = io.BytesIO()
    used: set[str] = set()

    def name(n: str) -> str:
        n = PurePath(n).name or "document"
        stem, suffix = PurePath(n).stem, PurePath(n).suffix
        out, i = n, 2
        while out in used:
            out, i = f"{stem} ({i}){suffix}", i + 1
        used.add(out)
        return out

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for snap_doc, doc in zip(sub["snapshot"].get("documents", []), view["documents"]):
            held = store.docs.get(doc["id"])
            files = getattr(held, "files", None) if held else None
            if files:
                for page, (data, _media) in zip(doc["pages"], files):
                    z.writestr(name(page["filename"]), data)
            else:
                z.writestr(name(f"{PurePath(snap_doc['filename']).stem}.txt"), (doc.get("text") or "").encode("utf-8"))
        z.writestr("verification-summary.txt", webmap.verification_summary(view["case"], view["documents"]).encode("utf-8"))
    store.audit("caseworker", "submission.pack", sub["id"], {"laa_ref": sub["laa_ref"]})
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="Gateway Check {sub["laa_ref"]}.zip"', "Cache-Control": "no-store"})


@router.post("/inbox", status_code=201)
async def inbox(request: Request, email: str = Form(""), files: list[UploadFile] = File(default=[])):
    """Draft a reply to an evidence-check query: check the attachments against the names in the email."""
    firm = _first(r"(?im)^(?:from|firm|regards,?)\s*:?\s*([^\n<]+?)\s*(?:<|$)", email)
    applicant = _first(r"(?i)\b(?:client|applicant)[:\s]+([A-Z][\w'-]+ [A-Z][\w'-]+)", email) or ""
    other = _first(r"(?i)\b(?:other party|respondent|perpetrator)[:\s]+([A-Z][\w'-]+ [A-Z][\w'-]+)", email)
    c = store.create_case(applicant, other, "Inbox query", "inbox", work_type="licensed", firm_name=firm or "", ask_label="")
    docs = []
    for f in files:
        text, needs, held, pages = await _ingest_files([f])
        doc = store.add_document(c["id"], pages[0]["filename"], "inbox", None, held[0][0], text, None, pages=pages)
        store.set_files(doc["id"], held)
        await core.run_check(c, doc, text, needs, held if needs else None)  # inbox mode waits for the answer
        docs.append(webmap.to_document(store, store.get_document(doc["id"]), _base(request)))
    return {"email": email, "firm": firm, "caseId": c["id"], "documents": docs, "reply": _inbox_reply(firm, docs)}


def _inbox_reply(firm: str | None, docs: list[dict]) -> str:
    parts = []
    for d in docs:
        r = d["result"]
        name = d["pages"][0]["filename"] + (f" (Schedule 1, paragraph {r['matchedPara']})" if r and r["matchedPara"] else "")
        key = webmap.doc_verdict_key(r)
        if key == "pass":
            parts.append(f"{name}: this meets the requirements.")
        elif key == "not_prescribed":
            parts.append(f"{name}: this is not one of the accepted evidence types.")
        elif key == "refer":
            parts.append(f"{name}: we need to check this further. {r['reason']}")
        else:
            missing = " ".join(e["explanation"] for e in r["elements"] if e["status"] != "met")
            met = [e["label"].lower() for e in r["elements"] if e["status"] == "met"]
            parts.append(f"{name}: this does not yet meet the requirements. {missing}" + (f"\n\nThe rest of the letter meets the requirements ({'; '.join(met)})." if met else ""))
    return "\n".join([f"Dear {firm or 'colleague'},", "", "Thank you for your query about the domestic abuse evidence.", "", "\n\n".join(parts), "",
                      "There is sample wording on GOV.UK: https://www.gov.uk/government/collections/sample-letters-to-get-evidence-of-domestic-violence",
                      "", "Kind regards,", "Gateway Evidence Check team"])


def _first(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------- #
# demo helpers: the stage view and the persona switcher
# --------------------------------------------------------------------------- #
DEMO_APPLICANT = "Jane Doe"


@router.get("/demo")
def demo_state():
    """The case the demo follows (Jane Doe, else the newest), with a live client link, and the first case in the queue."""
    cases = store.list_cases()
    if not cases:
        raise HTTPException(404, "no cases: run the seed")
    c = next((x for x in cases if x["applicant_name"] == DEMO_APPLICANT), cases[-1])
    link = store.latest_client_link(c["id"]) or store.create_client_link(c["id"], 7)
    queue = [s for s in store.list_submissions() if s["status"] == "submitted"]
    def token_for(case: dict) -> str:
        return (store.latest_client_link(case["id"]) or store.create_client_link(case["id"], 7))["token"]

    return {"caseId": c["id"], "ref": c["ref"], "applicantName": c["applicant_name"], "clientToken": link["token"],
            "queueCaseId": queue[0]["case_id"] if queue else None,
            "cases": [{"id": x["id"], "ref": x["ref"], "applicantName": x["applicant_name"], "clientToken": token_for(x)}
                      for x in cases if x.get("created_by") != "inbox"]}


@router.post("/demo/reset", status_code=202)
async def demo_reset(background: BackgroundTasks):
    """Wipe everything and re-seed the scripted demo cases (cached model answers make this quick)."""
    for table in ("cases", "documents", "document_files", "tracker_events", "evidence_requests", "client_links", "submissions", "decisions", "audit"):
        store._exec(f"DELETE FROM {table}")
    store.docs._items.clear()

    async def seed():
        from demo.seed_demo import CASES, iter_docs, write_corrected_letter

        for spec in CASES:
            case = store.create_case(spec["applicant_name"], spec["other_party_name"], spec["case_type"], "provider", work_type=spec["work_type"],
                                     firm_name="Hartley & Webb Solicitors", ask_label=spec.get("ask_label", "Letter from your support worker"),
                                     application_date=_today())
            # every demo client has a code ready on the solicitor's Client tab, to type on the client's start screen
            store.create_client_link(case["id"], 7)
            ids = []
            for fn, data, text, para, pages in iter_docs(spec):
                needs = not (text or "").strip()
                doc = store.add_document(case["id"], fn, "provider", para, data, text or "", pages=pages)
                media = (pages[0].get("contentType") if pages else None) or "application/octet-stream"
                store.set_files(doc["id"], [(data, media)])
                await core.run_check(case, doc, text or "", needs, [(data, media)] if needs else None)
                ids.append(doc["id"])
            if spec.get("submit"):
                sub = store.create_submission(case["id"], ids, "Demo submission", spec.get("reason"), "provider")
                await core.laa_check(sub)
        write_corrected_letter()

    from demo.seed_demo import CASES

    background.add_task(seed)
    return {"ok": True, "expected_cases": len(CASES)}


# --------------------------------------------------------------------------- #
@router.get("/documents/{document_id}/file/{page}")
def document_file(document_id: str, page: int):
    files = store.files(document_id)
    if not files or page >= len(files):
        raise HTTPException(410, "file no longer held")
    data, media_type = files[page]
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "no-store"})
