"""Map engine results and store rows to the frontend's TypeScript shapes
(web/src/lib/types.ts): Case, CaseDocument, CheckResult, ElementResult, Decision.

Vocabulary: meets -> pass, needs_change -> fail, needs_caseworker -> refer,
not_prescribed -> fail with matchedPara null; included/missing -> met/not_met.
Flags are human-readable sentences there, so codes are translated here.

Roles (who the JSON is for):
  provider    the solicitor on link 1: everything, including the client link and the selection
  caseworker  the LAA on link 2: built from the frozen submission snapshot, LAA reference as `ref`,
              no client link, ask label or selection (those never cross to the LAA)
  client      the applicant on link 1: plain words only. No document text, quotes, reasoning,
              flags, names, agreement or verification; just outcome, paragraph, the client
              message, the asks in plain words, a short organisation name and the letter date.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import PurePath

from app.store import Store

OUTCOME = {"meets": "pass", "needs_change": "fail", "needs_caseworker": "refer", "not_prescribed": "fail"}
STATUS = {"included": "met", "missing": "not_met", "unclear": "unclear"}
STATE = {"pass": "ready", "fail": "change", "refer": "check", "not_prescribed": "other"}

ROLES = ("provider", "caseworker", "client")
# What each role must never receive. Tests assert these keys are absent.
CASEWORKER_HIDDEN_CASE_KEYS = frozenset({"clientToken", "tokenExpiresAt", "askLabel", "selectedDocumentIds", "selectionTouched"})
CLIENT_HIDDEN_RESULT_KEYS = frozenset({"flags", "agreement", "victimName", "otherPartyName", "verification", "authorOrg", "authorRole"})
CLIENT_HIDDEN_ELEMENT_KEYS = frozenset({"quote", "explanation", "label"})
CLIENT_HIDDEN_DOCUMENT_KEYS = frozenset({"text"})
CLIENT_ERROR_MESSAGE = "We could not check this document automatically. Your solicitor will look at it."

FLAG_TEXT = {
    "hedge": "Hedged wording",
    "injection": "Document contains instructions to the reviewer",
    "non_english": "Not written in English",
    "name_mismatch": "Other party's name does not match the application",
    "victim_name_mismatch": "Applicant's name does not match the application",
    "classification_low_confidence": "Evidence type uncertain",
    "model_refusal": "The checker could not assess this document",
    "model_error": "The check could not be completed reliably; some model assessments failed",
    "illegible": "Document could not be read",
    "unfilled_placeholder": "Template placeholder left unfilled",
    "quote_not_found": "A quoted passage could not be found in the document",
    "quote_fuzzy_match": "A quote matched approximately, not word for word",
    "quote_multi_span": "A quote joins passages from different parts of the document",
}
CONTENT_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
                 ".gif": "image/gif", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".txt": "text/plain", ".eml": "message/rfc822"}
_ORG_STOP = {"domestic", "abuse", "violence", "women's", "womens", "support", "service", "services", "aid", "trust", "centre", "center",
             "outreach", "partnership", "project", "refuge", "housing", "association", "group", "homes", "charity", "ltd", "limited", "cic"}
_KEEP_FULL = re.compile(r"\b(surgery|practice|medical|health|hospital|nhs|council|borough|police|constabulary|court|home office|cafcass|clinic)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_type(filename: str) -> str:
    return CONTENT_TYPES.get(PurePath(filename).suffix.lower(), "application/octet-stream")


def firm_short(firm: str | None) -> str:
    return re.sub(r"\s+(Solicitors|LLP|Ltd)$", "", firm or "", flags=re.I)


def short_org(org: str | None) -> str | None:
    """Fallback when the classifier gave none: 'Brookfield' for 'Brookfield Women's Support Service'; full name for GPs, councils, police."""
    if not org:
        return None
    if _KEEP_FULL.search(org):
        return org
    words = org.replace("–", "-").split()
    kept = []
    for w in words:
        if w.lower().strip(",") in _ORG_STOP:
            break
        kept.append(w)
    return " ".join(kept) if kept else org


_DATE_WORDS = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", re.I)
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}


def first_iso_date(dates: list[str] | None) -> str | None:
    for d in dates or []:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return d
        m = _DATE_WORDS.search(d)
        if m:
            return f"{int(m.group(3)):04d}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def agreement(result: dict) -> str:
    k = result.get("votes") or 0
    counts = [max(e.get("votes", {}).values() or [0]) for e in result.get("elements", [])]
    m = min(counts) if counts else k
    return f"{m} of {k} checks agreed" if k else "checked once"


def flag_sentences(result: dict) -> list[str]:
    out: list[str] = []
    for f in result.get("flags", []):
        if f == "vote_disagreement":
            k = result.get("votes") or 0
            counts = [max(e.get("votes", {}).values() or [0]) for e in result.get("elements", [])]
            text = f"Checks disagreed ({min(counts) if counts else 0} of {k})"
        else:
            text = FLAG_TEXT.get(f, f.replace("_", " ").capitalize())
        if text not in out:
            out.append(text)
    return out


def _check_role(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")
    return role


def to_check_result(r: dict, role: str = "provider") -> dict:
    """CheckResult for the given role. The client gets the reduced shape (see client_result)."""
    full = _full_check_result(r)
    return client_result(full, r) if _check_role(role) == "client" else full


def client_result(full: dict, r: dict) -> dict:
    """Link 1, applicant side. The client screens use outcome, matchedPara, shortOrg, clientHint and fix;
    `reason` is the plain client message, never the provider summary, and authorName is null so the
    message to the letter writer never carries a name onto a phone someone else may read."""
    return {
        "matchedPara": full["matchedPara"], "outcome": full["outcome"],
        "reason": r.get("client_message") or "",
        "elements": [{"key": e["key"], "status": e["status"], "clientHint": e.get("clientHint"), "fix": e.get("fix")} for e in full["elements"]],
        "shortOrg": full["shortOrg"], "authorName": None, "letterDate": full["letterDate"],
        "rulesVersion": full["rulesVersion"], "checkedAt": full["checkedAt"],
    }


def _full_check_result(r: dict) -> dict:
    cls, parties = r.get("classification") or {}, r.get("parties") or {}
    verdict = r["verdict"]
    return {
        "matchedPara": None if verdict == "not_prescribed" else r.get("paragraph"),
        "outcome": OUTCOME[verdict],
        "reason": r.get("provider_summary") or "",
        "elements": [{"key": e["element_id"], "label": e["label"], "status": STATUS[e["status"]], "quote": e.get("quote"),
                      "explanation": e.get("reasoning") or "", "fix": e.get("fix"), "clientHint": e.get("client_hint")}
                     for e in r.get("elements", [])],
        "flags": flag_sentences(r),
        "authorOrg": cls.get("author_org"),
        "shortOrg": cls.get("short_org") or short_org(cls.get("author_org")),
        "authorName": cls.get("author_name"),
        "authorRole": cls.get("author_role"),
        "letterDate": cls.get("letter_date") or first_iso_date(parties.get("dates_mentioned")),
        "victimName": parties.get("victim_name"),
        "otherPartyName": parties.get("other_party_name"),
        "agreement": agreement(r),
        "verification": [{"id": v["id"], "label": v["label"], "status": v["status"], "detail": v["detail"], "link": v.get("link")} for v in r.get("verification", [])],
        "rulesVersion": r.get("rules_version") or "",
        "checkedAt": r.get("checked_at") or now_iso(),
    }


def error_result(message: str, role: str = "provider") -> dict:
    if _check_role(role) == "client":
        return {"matchedPara": None, "outcome": "refer", "reason": CLIENT_ERROR_MESSAGE, "elements": [], "shortOrg": None, "authorName": None,
                "letterDate": None, "rulesVersion": "", "checkedAt": now_iso()}
    return {"matchedPara": None, "outcome": "refer", "reason": f"The check could not be completed ({message}). A caseworker will look at it.",
            "elements": [], "flags": ["The checker could not assess this document"], "authorOrg": None, "shortOrg": None, "authorName": None,
            "authorRole": None, "letterDate": None, "victimName": None, "otherPartyName": None, "agreement": "not checked", "verification": [],
            "rulesVersion": "", "checkedAt": now_iso()}


def doc_verdict_key(result: dict | None) -> str:
    """Mirror of labels.ts docVerdict: refer wins, then a null paragraph means not_prescribed."""
    if result is None:
        return "checking"
    if result["outcome"] == "refer":
        return "refer"
    if result["matchedPara"] is None:
        return "not_prescribed"
    return result["outcome"]


def client_state(result: dict | None) -> str | None:
    key = doc_verdict_key(result)
    return STATE.get(key) if key != "checking" else None


def _pages(store: Store, doc_id: str, pages: list[dict] | None, filename: str, base_url: str) -> list[dict]:
    pages = [dict(p) for p in (pages or [{"filename": filename, "contentType": content_type(filename)}])]
    held = store.docs.get(doc_id)
    if held and getattr(held, "files", None):
        for i, p in enumerate(pages[: len(held.files)]):
            p["url"] = f"{base_url}/web/documents/{doc_id}/file/{i}"
    return pages


def _result_for(r: dict, text: str, role: str) -> dict:
    """Full result, quotes anchored to the text the reader will see, then reduced for the role."""
    full = _full_check_result(r)
    if text:
        _anchor_quotes(full, text)
    return client_result(full, r) if role == "client" else full


def _document(doc_id: str, case_id: str, pages: list[dict], text: str, uploaded_by: str, uploaded_at: str, result: dict | None, role: str) -> dict:
    out = {"id": doc_id, "caseId": case_id, "pages": pages, "text": text, "uploadedBy": uploaded_by, "uploadedAt": uploaded_at, "result": result}
    if role == "client":
        for k in CLIENT_HIDDEN_DOCUMENT_KEYS:
            out.pop(k, None)
    return out


def to_document(store: Store, d: dict, base_url: str = "", role: str = "provider") -> dict:
    """CaseDocument from the live document row (link 1). The caseworker's copy comes from the submission snapshot instead."""
    _check_role(role)
    text = store.document_text(d["id"]) or ""
    if d["status"] == "done" and d.get("result"):
        result = _result_for(d["result"], text, role)
    elif d["status"] == "error":
        result = error_result(d.get("error") or "error", role)
    else:
        result = None
    return _document(d["id"], d["case_id"], _pages(store, d["id"], d.get("pages"), d["filename"], base_url), text,
                     d["uploaded_by"], d["uploaded_at"], result, role)


def _anchor_quotes(result: dict, text: str) -> None:
    """The frontend highlights a quote only if it is a substring of the text. A quote that the
    verifier accepted across several passages (or with different quote marks) is replaced by the
    exact text of its longest verified span, so the annotation lands on the document."""
    from engine.verify import spans

    for e in result["elements"]:
        q = e.get("quote")
        if not q and e["status"] != "met":
            # The problem wording, if the explanation quotes it ("Victim testimony and referral"),
            # so the document view can mark the sentence that needs to change.
            for m in re.finditer(r"[\"\u201c']([^\"\u201d']{6,160})[\"\u201d']", e.get("explanation") or ""):
                found = spans(m.group(1), text)
                if found:
                    a, b = found[0]
                    e["quote"] = text[a:b]
                    break
            continue
        if not q or q in text:
            continue
        found = spans(q, text)
        if found:
            a, b = max(found, key=lambda s: s[1] - s[0])
            e["quote"] = text[a:b]


def default_selection(documents: list[dict]) -> list[str]:
    """Mirror of evidence.ts defaultSelection: the latest document that passes, by letter date then upload time."""
    passing = [d for d in documents if d["result"] and doc_verdict_key(d["result"]) == "pass"]
    if not passing:
        return []
    passing.sort(key=lambda d: (d["result"].get("letterDate") or d["uploadedAt"]), reverse=True)
    return [passing[0]["id"]]


def to_decision(d: dict | None) -> dict | None:
    if not d:
        return None
    return {"action": d["action"], "note": d.get("note") or "", "toolVerdict": d.get("tool_verdict") or "",
            "agreedWithTool": bool(d.get("agreed_with_tool")), "at": d["created_at"]}


def to_case(store: Store, c: dict, documents: list[dict], role: str = "provider") -> dict:
    """Case for the solicitor (link 1) from the live row. A caseworker's case is built from the
    submission snapshot by case_from_submission; this only strips what must not cross if asked."""
    _check_role(role)
    link = store.latest_client_link(c["id"])
    sub = store.latest_submission(c["id"])
    decision = sub["decisions"][-1] if sub and sub.get("decisions") else None
    touched = bool(c.get("selection_touched"))
    selected = json.loads(c["selected_json"]) if touched and c.get("selected_json") else default_selection(documents)
    out = {
        "id": c["id"], "ref": c["ref"], "firm": c.get("firm_name") or "",
        "applicantName": c.get("applicant_name") or "", "otherPartyName": c.get("other_party_name") or "",
        "caseType": c.get("case_type") or "", "createdAt": c["created_at"],
        "clientToken": link["token"] if link else None, "tokenExpiresAt": link["expires_at"] if link else None,
        "askLabel": c.get("ask_label") or "",
        "documentIds": [d["id"] for d in documents], "selectedDocumentIds": selected, "selectionTouched": touched,
        "submittedAt": sub["submitted_at"] if sub else None,
        "submittedDocumentIds": sub["document_ids"] if sub else [],
        "submitReason": sub.get("submit_anyway_reason") if sub else None,
        "decision": to_decision(decision),
        # the solicitor's handle on their own latest submission: the pack for Civil Apply is
        # GET /web/submissions/{submissionId}/pack.zip (null until the case is submitted)
        "submissionId": sub["id"] if sub else None,
    }
    if role == "caseworker":
        out["laaCheck"] = laa_check_summary(sub) if sub else None
        out["ref"] = sub["laa_ref"] if sub else ""
        for k in CASEWORKER_HIDDEN_CASE_KEYS:
            out.pop(k, None)
    return out


def case_with_documents(store: Store, c: dict, only_ids: list[str] | None = None, base_url: str = "", role: str = "provider") -> dict:
    """CaseWithDocuments from live data (link 1). For the caseworker, use submission_with_documents:
    the LAA sees the frozen pack, never the live case."""
    _check_role(role)
    rows = store.list_documents(c["id"])
    if only_ids is not None:
        rows = [r for r in rows if r["id"] in set(only_ids)]
    documents = [to_document(store, d, base_url, role) for d in rows]
    return {"case": to_case(store, c, documents, role), "documents": documents}


# --------------------------------------------------------------------------- #
# link 2: the frozen submission
# --------------------------------------------------------------------------- #
def laa_check_summary(sub: dict) -> dict:
    """{done, differences}: whether the LAA's independent check has run and how many element or verdict differences it found."""
    return {"done": sub.get("laa_check") is not None, "differences": len(sub.get("differences") or [])}


def snapshot_document(store: Store, sub: dict, d: dict, base_url: str = "", role: str = "caseworker") -> dict:
    """CaseDocument from one snapshot entry: the result and text as they were when submitted. A later
    re-check, name change, purge or TTL expiry on the live document changes nothing here. Snapshots
    made before snapshot_text existed fall back to the held text; the live row supplies only metadata."""
    doc_id = d["document_id"]
    live = store.get_document(doc_id) if ("uploaded_at" not in d or "pages" not in d) else None
    text = d["snapshot_text"] if "snapshot_text" in d else store.document_text(doc_id)
    text = text or ""
    result = _result_for(d["result"], text, role) if d.get("result") else None
    pages = _pages(store, doc_id, d.get("pages") or (live or {}).get("pages"), d["filename"], base_url)
    return _document(doc_id, sub["case_id"], pages, text, d.get("uploaded_by") or (live or {}).get("uploaded_by") or "provider",
                     d.get("uploaded_at") or (live or {}).get("uploaded_at") or sub["submitted_at"], result, role)


def case_from_submission(sub: dict, documents: list[dict]) -> dict:
    """The caseworker's Case: names and case type from the snapshot, the LAA reference as `ref`, this
    submission's decision, and nothing from link 1 (no case ref, client link, ask label or selection)."""
    app_ = sub["snapshot"].get("application") or {}
    decision = sub["decisions"][-1] if sub.get("decisions") else None
    return {
        "id": sub["case_id"], "ref": sub["laa_ref"], "firm": sub.get("firm_name") or "",
        "applicantName": app_.get("applicant_name") or "", "otherPartyName": app_.get("other_party_name") or "",
        "caseType": app_.get("case_type") or "", "createdAt": sub["submitted_at"],
        "documentIds": [d["id"] for d in documents],
        "submittedAt": sub["submitted_at"], "submittedDocumentIds": list(sub.get("document_ids") or []),
        "submitReason": sub.get("submit_anyway_reason"), "decision": to_decision(decision),
        "submissionId": sub["id"], "laaCheck": laa_check_summary(sub),
    }


def submission_with_documents(store: Store, sub: dict, role: str = "caseworker", base_url: str = "") -> dict:
    """CaseWithDocuments for one submission, entirely from its frozen snapshot. Used for the caseworker
    queue, the review screen, the decision and the pack download."""
    _check_role(role)
    documents = [snapshot_document(store, sub, d, base_url, role) for d in sub["snapshot"].get("documents", [])]
    return {"case": case_from_submission(sub, documents), "documents": documents}


def verification_summary(case: dict, documents: list[dict]) -> str:
    """Text pack for Civil Apply, mirroring outputs.ts verificationSummary."""
    labels = {"pass": "Meets the requirements", "fail": "Needs a change", "refer": "Needs a caseworker check", "not_prescribed": "Not an accepted evidence type"}
    blocks = []
    for d in documents:
        r = d["result"]
        title = d["pages"][0]["filename"] if d["pages"] else "Document"
        if not r:
            blocks.append(f"{title}: still being checked")
            continue
        rows = [f"  [{'x' if e['status'] == 'met' else ' '}] {e['label']}" + (f'\n      "{e["quote"]}"' if e.get("quote") else "") for e in r["elements"]]
        blocks.append("\n".join([title, f"  Evidence type: {('Schedule 1, paragraph ' + r['matchedPara']) if r['matchedPara'] else 'Not matched'}",
                                 f"  Result: {labels[doc_verdict_key(r)]}", f"  Agreement: {r['agreement']}", f"  Rules: {r['rulesVersion']}", *rows]))
    return "\n".join(["GATEWAY CHECK – VERIFICATION SUMMARY", "", f"Client: {case['applicantName']}",
                      f"Other party: {case['otherPartyName']}", f"Case: {case['ref']}", f"Firm: {case['firm']}", "", *blocks, "",
                      "This summary supports the caseworker's decision. The decision is theirs."])
