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
              POST /web/cases/{id}/submit          {documentIds, reason} -> {case, documents, summary, filename}
  Client      GET  /web/client/{token}             -> {firstName, firmName, askLabel, linkExpiresAt, latestDocument, state}
              POST /web/client/{token}/upload      multipart files[] -> {documentId}
              GET  /web/client/{token}/documents/{doc} -> {document, state}
  Caseworker  GET  /web/queue                      -> CaseWithDocuments[] (submitted, undecided; submitted documents only)
              GET  /web/queue/{id}                 -> CaseWithDocuments
              POST /web/queue/{id}/decision        {action, note} -> Decision
              POST /web/inbox                      multipart email, files[] -> {email, firm, documents, reply}
  Files       GET  /web/documents/{doc}/file/{page} -> the uploaded file while it is still held in memory
"""
from __future__ import annotations

import re

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


def _case(case_id: str) -> dict:
    c = store.get_case(case_id)
    if not c:
        raise HTTPException(404, "case not found")
    return c


def _base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


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
        held.append((data, ing.media_type or webmap.content_type(name)))
        pages.append({"filename": name, "contentType": webmap.content_type(name)})
    return "\n\n".join(texts), needs, held, pages


def _add_document(case: dict, uploaded_by: str, text: str, needs: bool, held: list, pages: list[dict],
                  replaces: str | None, background: BackgroundTasks) -> dict:
    doc = store.add_document(case["id"], pages[0]["filename"], uploaded_by, None, held[0][0] if held else None, text, replaces, pages=pages)
    item = store.docs.get(doc["id"])
    if item is not None:
        item.files = held
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
                          firm_name=body.firm or "Demo Family Law LLP", ask_label=body.askLabel)
    store.create_client_link(c["id"], 7)
    return webmap.case_with_documents(store, c, base_url=_base(request))


@router.post("/cases/from-letter", status_code=201)
async def case_from_letter(request: Request, background: BackgroundTasks, files: list[UploadFile] = File(...), firm: str | None = Form(None)):
    text, needs, held, pages = await _ingest_files(files)
    c = store.create_case("", None, "Child arrangements", "provider", work_type="licensed", firm_name=firm or "Demo Family Law LLP",
                          ask_label="Letter from your support worker")
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
def submit(case_id: str, body: Submit, request: Request):
    c = _case(case_id)
    docs = [store.get_document(d) for d in body.documentIds]
    docs = [d for d in docs if d and d["case_id"] == c["id"]]
    if not docs:
        raise HTTPException(400, "choose at least one document")
    if any(d["status"] == "checking" for d in docs):
        raise HTTPException(409, "a chosen document is still being checked")
    store.create_submission(c["id"], [d["id"] for d in docs], None, body.reason, "provider")
    out = webmap.case_with_documents(store, c, only_ids=[d["id"] for d in docs], base_url=_base(request))
    out["summary"] = webmap.verification_summary(out["case"], out["documents"])
    out["filename"] = f"Gateway Check {c['ref']}.txt"
    return out


# --------------------------------------------------------------------------- #
# client
# --------------------------------------------------------------------------- #
def _client_case(token: str) -> dict:
    link = store.resolve_client_link(token)
    if not link:
        raise HTTPException(404, "link not found or expired")
    return store.get_case(link["case_id"])


@router.get("/client/{token}")
def client_view(token: str, request: Request):
    c = _client_case(token)
    link = store.latest_client_link(c["id"])
    docs = [webmap.to_document(store, d, _base(request)) for d in store.list_documents(c["id"]) if d["uploaded_by"] == "client"]
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
    c = _client_case(token)
    d = store.get_document(document_id)
    if not d or d["case_id"] != c["id"]:
        raise HTTPException(404, "document not found")
    doc = webmap.to_document(store, d, _base(request))
    return {"document": doc, "state": webmap.client_state(doc["result"])}


# --------------------------------------------------------------------------- #
# caseworker
# --------------------------------------------------------------------------- #
def _queue_items(request: Request, only_case: str | None = None) -> list[dict]:
    items = []
    for s in store.list_submissions():
        if s["status"] != "submitted" and only_case is None:
            continue
        c = store.get_case(s["case_id"])
        if not c or (only_case and c["id"] != only_case and c["ref"] != only_case and s["id"] != only_case):
            continue
        # one row per case: its latest submission
        if any(i["case"]["id"] == c["id"] for i in items):
            continue
        items.append(webmap.case_with_documents(store, c, only_ids=s["document_ids"], base_url=_base(request)))
    return items


@router.get("/queue")
def queue(request: Request):
    return _queue_items(request)


@router.get("/queue/{case_id}")
def review(case_id: str, request: Request):
    items = _queue_items(request, only_case=case_id)
    if not items:
        raise HTTPException(404, "no submission for that case")
    return items[0]


@router.post("/queue/{case_id}/decision", status_code=201)
def decide(case_id: str, body: DecisionIn):
    c = _case(case_id)
    sub = store.latest_submission(c["id"])
    if not sub:
        raise HTTPException(404, "no submission for that case")
    d = store.add_decision(sub["id"], body.caseworker, body.action, body.note or None)
    return {"action": d["action"], "note": d.get("note") or "", "toolVerdict": d.get("tool_verdict") or "",
            "agreedWithTool": bool(d.get("agreed_with_tool")), "at": d["created_at"]}


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
        item = store.docs.get(doc["id"])
        if item is not None:
            item.files = held
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
    return {"caseId": c["id"], "ref": c["ref"], "applicantName": c["applicant_name"], "clientToken": link["token"],
            "queueCaseId": queue[0]["case_id"] if queue else None,
            "cases": [{"id": x["id"], "ref": x["ref"], "applicantName": x["applicant_name"]} for x in cases]}


@router.post("/demo/reset", status_code=202)
async def demo_reset(background: BackgroundTasks):
    """Wipe everything and re-seed the scripted demo cases (cached model answers make this quick)."""
    for table in ("cases", "documents", "tracker_events", "evidence_requests", "client_links", "submissions", "decisions", "audit"):
        store._exec(f"DELETE FROM {table}")
    store.docs._items.clear()

    async def seed():
        from demo.seed_demo import CASES, CORRECTED_A, ROOT
        from engine.pipeline import check_text

        for spec in CASES:
            case = store.create_case(spec["applicant_name"], spec["other_party_name"], spec["case_type"], "provider", work_type=spec["work_type"],
                                     firm_name="Hartley & Webb Solicitors", ask_label=spec.get("ask_label", "Letter from your support worker"))
            ids = []
            for fn, text, para in spec["docs"]:
                doc = store.add_document(case["id"], fn, "provider", para, None, text)
                res = await check_text(text, fn, core.application_for(case), rules=core.rules(), llm=core.state["llm"], claimed_para=para, document_id=doc["id"])
                store.set_document_result(doc["id"], res.model_dump())
                ids.append(doc["id"])
            if spec.get("submit"):
                store.create_submission(case["id"], ids, "Demo submission", spec.get("reason"), "provider")
        out = ROOT / "demo" / "files"
        out.mkdir(exist_ok=True)
        (out / "case-a-support-letter-corrected.txt").write_text(CORRECTED_A)

    background.add_task(seed)
    return {"ok": True, "expected_cases": 7}


# --------------------------------------------------------------------------- #
@router.get("/documents/{document_id}/file/{page}")
def document_file(document_id: str, page: int):
    item = store.docs.get(document_id)
    files = getattr(item, "files", None) if item else None
    if not files or page >= len(files):
        raise HTTPException(410, "file no longer held")
    data, media_type = files[page]
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "no-store"})
