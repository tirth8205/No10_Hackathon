"""JSON API for the three surfaces. The frontend (server-rendered templates or a
separate client) calls these; templates are not served from here.

Run:  .venv/bin/uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.store import Store
from engine import outputs
from engine.config import settings
from engine.ingest import UnsupportedFile, ingest
from engine.llm import get_llm
from engine.models import Application
from engine.pipeline import check_text
from engine.rules import RuleLoadError, RuleSet, load_rules
from engine.verify import spans

app = FastAPI(title="Gateway Check API", version="0.1.0",
              description="Checks domestic abuse evidence for legal aid against Schedule 1. Prototype: synthetic data only.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = Store()
state: dict[str, Any] = {"rules": load_rules(), "llm": get_llm()}


def rules() -> RuleSet:
    return state["rules"]


# --------------------------------------------------------------------------- #
# schemas
# --------------------------------------------------------------------------- #
class CaseIn(BaseModel):
    applicant_name: str
    other_party_name: str | None = None
    case_type: str | None = "Child arrangements order"
    work_type: str | None = Field(default=None, description="controlled | licensed | null")
    application_date: str | None = Field(default=None, description="ISO date of the legal aid application")
    created_by: str = "provider"
    safe_contact_method: str | None = None
    safe_contact_value: str | None = None
    safe_times: str | None = None
    firm_name: str | None = "Demo Family Law LLP"


class CaseUpdate(BaseModel):
    applicant_name: str | None = None
    other_party_name: str | None = None
    case_type: str | None = None
    work_type: str | None = None
    application_date: str | None = None
    status: str | None = None
    safe_contact_method: str | None = None
    safe_contact_value: str | None = None
    safe_times: str | None = None


class TextDocIn(BaseModel):
    text: str
    filename: str = "letter.txt"
    claimed_para: str | None = None
    uploaded_by: str = "provider"
    replaces_document_id: str | None = None


class SubmissionIn(BaseModel):
    document_ids: list[str]
    notes: str | None = None
    submit_anyway_reason: str | None = None
    resubmission_of: str | None = None
    actor: str = "provider"


class DecisionIn(BaseModel):
    action: str = Field(pattern="^(accept|return|refer)$")
    note: str | None = None
    caseworker: str = "caseworker"


class EventIn(BaseModel):
    event_type: str = "message"
    applicant_text: str
    solicitor_text: str | None = None
    created_by: str = "provider"
    visible_to_applicant: bool = True


class ReleaseIn(BaseModel):
    applicant_text: str | None = None
    actor: str = "provider"


class RequestIn(BaseModel):
    recipient: str | None = None
    text: str | None = None
    actor: str = "provider"


# --------------------------------------------------------------------------- #
# health, rules
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"ok": True, "llm": state["llm"].name, "rules": len(rules().rules), "rules_version": rules().gateway.rules_version,
            "api_key": settings.has_api_key, "votes": settings.votes, "cache": settings.cache}


@app.get("/api/rules")
def list_rules():
    return [{"id": r.id, "paragraph": r.paragraph, "name": r.name, "short_name": r.short_name, "legal_ref": r.legal_ref,
             "guidance_ref": r.guidance_ref, "enabled": r.enabled, "names_other_party_required": r.names_other_party_required,
             "applicant_must_be_victim": r.applicant_must_be_victim, "always_needs_caseworker": r.always_needs_caseworker,
             "gov_template_url": r.gov_template_url, "share_of_applications": r.share_of_applications,
             "elements": [{"id": e.id, "label": e.label, "requirement": e.requirement} for e in r.elements]}
            for r in sorted(rules().rules.values(), key=lambda r: (len(r.paragraph), r.paragraph))]


@app.post("/api/rules/reload")
def reload_rules():
    try:
        state["rules"] = load_rules()
    except RuleLoadError as e:
        raise HTTPException(400, str(e))
    store.audit("provider", "rules.reload", "rules", {"count": len(state["rules"].rules)})
    return {"ok": True, "rules": len(state["rules"].rules)}


# --------------------------------------------------------------------------- #
# cases (link 1)
# --------------------------------------------------------------------------- #
@app.post("/api/cases", status_code=201)
def create_case(body: CaseIn):
    return store.create_case(**body.model_dump())


@app.get("/api/cases")
def list_cases():
    out = []
    for c in store.list_cases():
        docs = store.list_documents(c["id"], include_superseded=False)
        out.append({**c, "case_verdict": _case_verdict(docs), "documents": len(docs),
                    "checking": any(d["status"] == "checking" for d in docs)})
    return out


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, include_superseded: bool = True):
    c = _case(case_id)
    docs = store.list_documents(c["id"], include_superseded)
    return {**c, "case_verdict": _case_verdict([d for d in docs if not d.get("replaces_document_id") or True]),
            "documents": docs, "events": store.list_events(c["id"]), "requests": store.list_requests(c["id"]),
            "submissions": [{k: v for k, v in s.items() if k not in ("snapshot", "laa_check")} for s in store.list_submissions() if s["case_id"] == c["id"]]}


@app.patch("/api/cases/{case_id}")
def update_case(case_id: str, body: CaseUpdate):
    c = _case(case_id)
    store.audit(body.model_dump().get("actor", "provider"), "case.update", c["id"], body.model_dump(exclude_none=True))
    return store.update_case(c["id"], **body.model_dump(exclude_none=True))


@app.get("/api/cases/{case_id}/status")
def case_status(case_id: str):
    """Small payload for polling (HTMX every 2 s)."""
    c = _case(case_id)
    docs = store.list_documents(c["id"], include_superseded=False)
    return {"case_id": c["id"], "ref": c["ref"], "case_verdict": _case_verdict(docs),
            "documents": [{"id": d["id"], "filename": d["filename"], "version": d["version"], "status": d["status"], "verdict": d["verdict"],
                           "uploaded_by": d["uploaded_by"], "paragraph": (d["result"] or {}).get("paragraph"),
                           "provider_summary": (d["result"] or {}).get("provider_summary"), "client_message": (d["result"] or {}).get("client_message")}
                          for d in docs]}


@app.post("/api/cases/{case_id}/documents", status_code=202)
async def upload_document(case_id: str, background: BackgroundTasks, file: UploadFile = File(...), claimed_para: str | None = Form(None),
                          uploaded_by: str = Form("provider"), replaces_document_id: str | None = Form(None)):
    c = _case(case_id)
    data = await file.read()
    try:
        ing = ingest(data, file.filename or "upload")
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    doc = store.add_document(c["id"], file.filename or "upload", uploaded_by, claimed_para, data if ing.needs_transcription else None, ing.text, replaces_document_id)
    background.add_task(_run_check, c, doc, ing.text, ing.needs_transcription, data if ing.needs_transcription else None, ing.media_type)
    return doc


@app.post("/api/cases/{case_id}/documents/text", status_code=202)
async def upload_text(case_id: str, body: TextDocIn, background: BackgroundTasks):
    c = _case(case_id)
    doc = store.add_document(c["id"], body.filename, body.uploaded_by, body.claimed_para, None, body.text, body.replaces_document_id)
    background.add_task(_run_check, c, doc, body.text, False, None, None)
    return doc


async def _run_check(case: dict, doc: dict, text: str, needs_transcription: bool, data: bytes | None, media_type: str | None):
    llm = state["llm"]
    try:
        if needs_transcription and data:
            tr = await llm.transcribe(data, media_type)
            if tr.text.strip():
                text = tr.text
                store.docs.set_text(doc["id"], text)
        res = await check_text(text, doc["filename"], Application(applicant_name=case["applicant_name"], other_party_name=case["other_party_name"], case_type=case["case_type"], application_date=case.get("application_date")),
                               rules=rules(), llm=llm, claimed_para=doc["claimed_para"], document_id=doc["id"])
        store.set_document_result(doc["id"], res.model_dump())
    except Exception as e:  # surface, never hang the UI
        store.set_document_result(doc["id"], None, f"{type(e).__name__}: {e}")


@app.get("/api/cases/{case_id}/documents/{document_id}")
def get_document(case_id: str, document_id: str, highlight: bool = False):
    c = _case(case_id)
    d = _doc(c, document_id)
    if highlight and d["result"]:
        d["highlights"] = _highlights(d)
    return d


@app.get("/api/cases/{case_id}/documents/{document_id}/text", response_class=PlainTextResponse)
def get_document_text(case_id: str, document_id: str):
    c = _case(case_id)
    _doc(c, document_id)
    item = store.docs.get(document_id)
    if not item or item.text is None:
        raise HTTPException(410, "document text no longer held (purged or expired)")
    return item.text


@app.post("/api/cases/{case_id}/documents/{document_id}/recheck", status_code=202)
async def recheck(case_id: str, document_id: str, background: BackgroundTasks, claimed_para: str | None = Query(None)):
    c = _case(case_id)
    d = _doc(c, document_id)
    item = store.docs.get(document_id)
    if not item or item.text is None:
        raise HTTPException(410, "document text no longer held; upload it again")
    if claimed_para is not None:
        store._exec("UPDATE documents SET claimed_para=? WHERE id=?", (claimed_para, document_id))
        d["claimed_para"] = claimed_para
    store._exec("UPDATE documents SET status='checking' WHERE id=?", (document_id,))
    background.add_task(_run_check, c, d, item.text, False, None, None)
    return {"ok": True}


@app.get("/api/cases/{case_id}/documents/{document_id}/request-letter", response_class=PlainTextResponse)
def request_letter(case_id: str, document_id: str):
    c = _case(case_id)
    d = _doc(c, document_id)
    letter = (d["result"] or {}).get("request_letter")
    if not letter:
        raise HTTPException(404, "no request letter: the document has no gaps or has not been checked")
    return letter


@app.post("/api/cases/{case_id}/documents/{document_id}/requests", status_code=201)
def draft_request(case_id: str, document_id: str, body: RequestIn):
    c = _case(case_id)
    d = _doc(c, document_id)
    text = body.text or (d["result"] or {}).get("request_letter")
    if not text:
        raise HTTPException(400, "nothing to request")
    recipient = body.recipient or ((d["result"] or {}).get("classification") or {}).get("author_org")
    return store.add_request(c["id"], document_id, recipient, text, body.actor)


@app.post("/api/requests/{request_id}/sent")
def request_sent(request_id: str, actor: str = "provider"):
    req = store.mark_request_sent(request_id, actor)
    if not req:
        raise HTTPException(404, "request not found")
    return req


@app.post("/api/cases/{case_id}/purge")
def purge(case_id: str, actor: str = "provider"):
    c = _case(case_id)
    return {"purged": store.purge_case_documents(c["id"], actor)}


# tracker
@app.get("/api/cases/{case_id}/events")
def events(case_id: str, view: str = "solicitor"):
    c = _case(case_id)
    return store.list_events(c["id"], applicant_view=(view == "applicant"))


@app.post("/api/cases/{case_id}/events", status_code=201)
def add_event(case_id: str, body: EventIn):
    c = _case(case_id)
    return store.add_event(c["id"], body.event_type, body.applicant_text, body.solicitor_text or body.applicant_text, body.created_by, body.visible_to_applicant)


@app.post("/api/events/{event_id}/release")
def release_event(event_id: str, body: ReleaseIn):
    ev = store.release_event(event_id, body.actor, body.applicant_text)
    if not ev:
        raise HTTPException(404, "event not found")
    return ev


# client link (applicant side)
@app.post("/api/cases/{case_id}/client-link", status_code=201)
def client_link(case_id: str, days: int = 7, actor: str = "provider"):
    c = _case(case_id)
    link = store.create_client_link(c["id"], days)
    store.audit(actor, "client_link.create", c["id"])
    return link


@app.delete("/api/cases/{case_id}/client-link")
def revoke_links(case_id: str, actor: str = "provider"):
    c = _case(case_id)
    store.revoke_client_links(c["id"])
    store.audit(actor, "client_link.revoke", c["id"])
    return {"ok": True}


@app.get("/api/client/{token}")
def client_view(token: str):
    """Applicant view: first name only, plain-language results, no legal reasoning, no LAA detail."""
    link = store.resolve_client_link(token)
    if not link:
        raise HTTPException(404, "link not found or expired")
    c = store.get_case(link["case_id"])
    docs = store.list_documents(c["id"], include_superseded=False)
    return {"ref": c["ref"], "first_name": c["applicant_first_name"],
            "documents": [{"id": d["id"], "filename": d["filename"], "status": d["status"],
                           "message": (d["result"] or {}).get("client_message") or ("We are checking this document." if d["status"] == "checking" else "Your solicitor will look at this document.")}
                          for d in docs],
            "events": store.list_events(c["id"], applicant_view=True),
            "nothing_yet": "You do not need everything. One strong document is usually enough." if not docs else None}


@app.post("/api/client/{token}/upload", status_code=202)
async def client_upload(token: str, background: BackgroundTasks, file: UploadFile = File(...)):
    link = store.resolve_client_link(token)
    if not link:
        raise HTTPException(404, "link not found or expired")
    c = store.get_case(link["case_id"])
    data = await file.read()
    try:
        ing = ingest(data, file.filename or "upload")
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    doc = store.add_document(c["id"], file.filename or "upload", "client", None, data if ing.needs_transcription else None, ing.text)
    background.add_task(_run_check, c, doc, ing.text, ing.needs_transcription, data if ing.needs_transcription else None, ing.media_type)
    return {"id": doc["id"], "status": "checking", "message": "Thank you. We are checking your document."}


# --------------------------------------------------------------------------- #
# submissions (link 2)
# --------------------------------------------------------------------------- #
@app.post("/api/cases/{case_id}/submissions", status_code=201)
async def create_submission(case_id: str, body: SubmissionIn, background: BackgroundTasks, independent_check: bool = True):
    c = _case(case_id)
    docs = [_doc(c, d) for d in body.document_ids]
    if not docs:
        raise HTTPException(400, "choose at least one checked document")
    if any(d["status"] != "done" for d in docs):
        raise HTTPException(409, "a chosen document is still being checked")
    verdicts = [d["result"]["verdict"] for d in docs]
    if "meets" not in verdicts and not body.submit_anyway_reason:
        raise HTTPException(422, {"message": "This is likely to be returned. Fix first, or give a reason to submit anyway.",
                                  "verdicts": {d["id"]: d["result"]["verdict"] for d in docs}})
    sub = store.create_submission(c["id"], [d["id"] for d in docs], body.notes, body.submit_anyway_reason, body.actor, body.resubmission_of)
    if independent_check:
        background.add_task(_laa_check, sub)
    return sub


async def _laa_check(sub: dict):
    """The LAA runs its own check on what was submitted and records any difference."""
    snap = sub["snapshot"]
    app_ = Application(**snap["application"])
    results, diffs = [], []
    for d in snap["documents"]:
        item = store.docs.get(d["document_id"])
        text = item.text if item and item.text else None
        if text is None:
            results.append({"document_id": d["document_id"], "error": "text no longer held"})
            continue
        try:
            res = await check_text(text, d["filename"], app_, rules=rules(), llm=state["llm"], claimed_para=d["claimed_para"], document_id=d["document_id"])
        except Exception as e:
            results.append({"document_id": d["document_id"], "error": str(e)})
            continue
        r = res.model_dump()
        results.append(r)
        prov = {e["element_id"]: e["status"] for e in d["result"]["elements"]}
        laa = {e["element_id"]: e["status"] for e in r["elements"]}
        for k in set(prov) | set(laa):
            if prov.get(k) != laa.get(k):
                diffs.append({"document_id": d["document_id"], "element_id": k, "provider": prov.get(k), "laa": laa.get(k)})
        if d["result"]["verdict"] != r["verdict"]:
            diffs.append({"document_id": d["document_id"], "element_id": None, "provider": d["result"]["verdict"], "laa": r["verdict"]})
    store.set_laa_check(sub["id"], {"documents": results, "checked_at": store.get_submission(sub["id"])["submitted_at"]}, diffs)


@app.get("/api/submissions")
def queue(status: str | None = None):
    subs = store.list_submissions()
    if status:
        subs = [s for s in subs if s["status"] == status]
    return [{k: v for k, v in s.items() if k not in ("snapshot", "laa_check")} | {
        "paragraphs": sorted({d["result"].get("paragraph") for d in s["snapshot"]["documents"] if d["result"].get("paragraph")}),
        "flags": sorted({f for d in s["snapshot"]["documents"] for f in d["result"].get("flags", [])}),
        "applicant_name": s["snapshot"]["application"]["applicant_name"],
        "laa_check_done": s["laa_check"] is not None, "differences": len(s["differences"])} for s in subs]


@app.get("/api/submissions/{submission_id}")
def get_submission(submission_id: str, highlight: bool = True):
    s = store.get_submission(submission_id)
    if not s:
        raise HTTPException(404, "submission not found")
    if highlight:
        for d in s["snapshot"]["documents"]:
            item = store.docs.get(d["document_id"])
            d["text"] = item.text if item and item.text else None
            d["highlights"] = _highlights({"result": d["result"]}, d["text"]) if d["text"] else []
    s["return_note"] = "\n\n".join(outputs.return_note(_as_doc_result(d["result"]), rules().get(d["result"].get("rule_id") or ""))
                                   for d in s["snapshot"]["documents"] if d["result"]["verdict"] != "meets") or None
    return s


@app.get("/api/submissions/{submission_id}/return-note", response_class=PlainTextResponse)
def return_note(submission_id: str):
    s = get_submission(submission_id, highlight=False)
    return s["return_note"] or "The evidence appears to meet the requirements; no return note is needed."


@app.post("/api/submissions/{submission_id}/decision", status_code=201)
def decide(submission_id: str, body: DecisionIn):
    s = store.get_submission(submission_id)
    if not s:
        raise HTTPException(404, "submission not found")
    return store.add_decision(s["id"], body.caseworker, body.action, body.note)


@app.get("/api/audit")
def audit(record: str | None = None):
    return store.list_audit(record)


SCOREBOARD_SETS = {"synthetic": "syn-v3-final", "style": "style-v3", "gold": "gold-v3-final"}


@app.get("/api/scoreboard")
def scoreboard():
    """Summaries of the three result sets (synthetic, unseen style, MoJ gold) plus the latest run."""
    results = Path(__file__).resolve().parent.parent / "eval" / "results"
    out = {"available": False, "sets": {}}
    for key, name in SCOREBOARD_SETS.items():
        f = results / f"{name}.json"
        if f.exists():
            out["sets"][key] = json.loads(f.read_text())["summary"]
            out["available"] = True
    latest = results / "latest.json"
    if latest.exists():
        out["latest"] = json.loads(latest.read_text())["summary"]
        out["available"] = True
    out["target"] = {"agreement": "0.90 to 0.95 (MoJ success criterion)", "false_approval_rate": "as close to 0 as possible"}
    return out


# --------------------------------------------------------------------------- #
def _case(case_id: str) -> dict:
    c = store.get_case(case_id)
    if not c:
        raise HTTPException(404, "case not found")
    return c


def _doc(case: dict, document_id: str) -> dict:
    d = store.get_document(document_id)
    if not d or d["case_id"] != case["id"]:
        raise HTTPException(404, "document not found")
    return d


def _case_verdict(docs: list[dict]) -> str:
    verdicts = [d["verdict"] for d in docs if d.get("verdict")]
    if "meets" in verdicts:
        return "meets"
    if "needs_caseworker" in verdicts:
        return "needs_caseworker"
    if "needs_change" in verdicts:
        return "needs_change"
    return "no_evidence_yet"


def _highlights(d: dict, text: str | None = None) -> list[dict]:
    """Character offsets of each verified quote in the document text, for <mark> rendering."""
    if text is None:
        item = store.docs.get(d.get("id", ""))
        text = item.text if item and item.text else None
    if not text:
        return []
    out = []
    for e in d["result"].get("elements", []):
        if e.get("quote") and e.get("status") == "included":
            for start, end in spans(e["quote"], text):
                out.append({"element_id": e["element_id"], "start": start, "end": end})
    return out


def _as_doc_result(r: dict):
    from engine.models import DocumentResult

    return DocumentResult.model_validate(r)
