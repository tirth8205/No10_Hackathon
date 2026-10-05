"""Map engine results and store rows to the frontend's TypeScript shapes
(web/src/lib/types.ts): Case, CaseDocument, CheckResult, ElementResult, Decision.

Vocabulary: meets -> pass, needs_change -> fail, needs_caseworker -> refer,
not_prescribed -> fail with matchedPara null; included/missing -> met/not_met.
Flags are human-readable sentences there, so codes are translated here.
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

FLAG_TEXT = {
    "hedge": "Hedged wording",
    "injection": "Document contains instructions to the reviewer",
    "non_english": "Not written in English",
    "name_mismatch": "Other party's name does not match the application",
    "victim_name_mismatch": "Applicant's name does not match the application",
    "classification_low_confidence": "Evidence type uncertain",
    "model_refusal": "The checker could not assess this document",
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


def to_check_result(r: dict) -> dict:
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
        "rulesVersion": r.get("rules_version") or "",
        "checkedAt": r.get("checked_at") or now_iso(),
    }


def error_result(message: str) -> dict:
    return {"matchedPara": None, "outcome": "refer", "reason": f"The check could not be completed ({message}). A caseworker will look at it.",
            "elements": [], "flags": ["The checker could not assess this document"], "authorOrg": None, "shortOrg": None, "authorName": None,
            "authorRole": None, "letterDate": None, "victimName": None, "otherPartyName": None, "agreement": "not checked",
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


def to_document(store: Store, d: dict, base_url: str = "") -> dict:
    held = store.docs.get(d["id"])
    pages = d.get("pages") or [{"filename": d["filename"], "contentType": content_type(d["filename"])}]
    pages = [dict(p) for p in pages]
    if held and getattr(held, "files", None):
        for i, p in enumerate(pages[: len(held.files)]):
            p["url"] = f"{base_url}/web/documents/{d['id']}/file/{i}"
    text = store.document_text(d["id"]) or ""
    if d["status"] == "done" and d.get("result"):
        result = to_check_result(d["result"])
        if text:
            _anchor_quotes(result, text)
    elif d["status"] == "error":
        result = error_result(d.get("error") or "error")
    else:
        result = None
    return {"id": d["id"], "caseId": d["case_id"], "pages": pages, "text": text,
            "uploadedBy": d["uploaded_by"], "uploadedAt": d["uploaded_at"], "result": result}


def _anchor_quotes(result: dict, text: str) -> None:
    """The frontend highlights a quote only if it is a substring of the text. A quote that the
    verifier accepted across several passages (or with different quote marks) is replaced by the
    exact text of its longest verified span, so the annotation lands on the document."""
    from engine.verify import spans

    for e in result["elements"]:
        q = e.get("quote")
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


def to_case(store: Store, c: dict, documents: list[dict]) -> dict:
    link = store.latest_client_link(c["id"])
    sub = store.latest_submission(c["id"])
    decision = sub["decisions"][-1] if sub and sub.get("decisions") else None
    touched = bool(c.get("selection_touched"))
    selected = json.loads(c["selected_json"]) if touched and c.get("selected_json") else default_selection(documents)
    return {
        "id": c["id"], "ref": c["ref"], "firm": c.get("firm_name") or "",
        "applicantName": c.get("applicant_name") or "", "otherPartyName": c.get("other_party_name") or "",
        "caseType": c.get("case_type") or "", "createdAt": c["created_at"],
        "clientToken": link["token"] if link else None, "tokenExpiresAt": link["expires_at"] if link else None,
        "askLabel": c.get("ask_label") or "",
        "documentIds": [d["id"] for d in documents], "selectedDocumentIds": selected, "selectionTouched": touched,
        "submittedAt": sub["submitted_at"] if sub else None,
        "submittedDocumentIds": sub["document_ids"] if sub else [],
        "submitReason": sub.get("submit_anyway_reason") if sub else None,
        "decision": {"action": decision["action"], "note": decision.get("note") or "", "toolVerdict": decision.get("tool_verdict") or "",
                     "agreedWithTool": bool(decision.get("agreed_with_tool")), "at": decision["created_at"]} if decision else None,
    }


def case_with_documents(store: Store, c: dict, only_ids: list[str] | None = None, base_url: str = "") -> dict:
    rows = store.list_documents(c["id"])
    if only_ids is not None:
        rows = [r for r in rows if r["id"] in set(only_ids)]
    documents = [to_document(store, d, base_url) for d in rows]
    return {"case": to_case(store, c, documents), "documents": documents}


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
    return "\n".join(["GATEWAY CHECK – VERIFICATION SUMMARY (PROTOTYPE, SYNTHETIC DATA)", "", f"Client: {case['applicantName']}",
                      f"Other party: {case['otherPartyName']}", f"Case: {case['ref']}", f"Firm: {case['firm']}", "", *blocks, "",
                      "This summary supports the caseworker's decision. The decision is theirs."])
