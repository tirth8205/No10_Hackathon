"""The /web layer must return exactly the shapes in web/src/lib/types.ts."""
import json
import os
import tempfile

from app import webmap
from app.store import Store

RESULT = {
    "document_id": "d1", "filename": "refuge.txt", "verdict": "needs_change", "paragraph": "18", "rule_id": "sch1_p18_refuge_refusal",
    "classification": {"rule_id": "sch1_p18_refuge_refusal", "confidence": "high", "document_kind": "letter", "author_name": "John Smith",
                       "author_org": "Brookfield Women's Support Service", "author_role": "Domestic Abuse Support Officer", "short_org": None,
                       "letter_date": None, "language": "en", "rationale": ""},
    "parties": {"victim_name": "Jane Doe", "other_party_name": None, "dates_mentioned": ["28th September 2026"]},
    "elements": [
        {"element_id": "perpetrator_named", "label": "B named", "status": "missing", "quote": None, "quote_verified": False,
         "votes": {"included": 0, "missing": 3, "unclear": 0}, "reasoning": "No perpetrator is named.", "fix": "Name the other party.", "client_hint": "name the person you needed to get away from"},
        {"element_id": "refusal_date", "label": "Date of refusal", "status": "included", "quote": "on 28th September 2026", "quote_verified": True,
         "votes": {"included": 2, "missing": 0, "unclear": 1}, "reasoning": "Date given.", "fix": None, "client_hint": None},
    ],
    "flags": ["vote_disagreement", "hedge", "unfilled_placeholder"], "provider_summary": "Paragraph 18: 1 of 2 requirements included.",
    "rules_version": "schedule1-v15-2026-06-15", "votes": 3, "checked_at": "2026-10-05T12:00:00+00:00",
}


def test_check_result_shape_and_vocabulary():
    r = webmap.to_check_result(RESULT)
    assert set(r) == {"matchedPara", "outcome", "reason", "elements", "flags", "authorOrg", "shortOrg", "authorName", "authorRole",
                      "letterDate", "victimName", "otherPartyName", "agreement", "verification", "rulesVersion", "checkedAt"}
    assert r["outcome"] == "fail" and r["matchedPara"] == "18"
    assert [e["status"] for e in r["elements"]] == ["not_met", "met"]
    assert set(r["elements"][0]) == {"key", "label", "status", "quote", "explanation", "fix", "clientHint"}
    assert r["elements"][0]["clientHint"] == "name the person you needed to get away from"
    assert r["agreement"] == "2 of 3 checks agreed"
    assert r["flags"] == ["Checks disagreed (2 of 3)", "Hedged wording", "Template placeholder left unfilled"]
    assert r["shortOrg"] == "Brookfield"              # derived when the classifier gave none
    assert r["letterDate"] == "2026-09-28"             # parsed from the dates mentioned
    assert r["checkedAt"] == "2026-10-05T12:00:00+00:00"


def test_not_prescribed_and_refer_map_like_the_frontend():
    np = webmap.to_check_result({**RESULT, "verdict": "not_prescribed", "paragraph": None, "elements": [], "flags": []})
    assert np["outcome"] == "fail" and np["matchedPara"] is None
    assert webmap.doc_verdict_key(np) == "not_prescribed" and webmap.client_state(np) == "other"
    rf = webmap.to_check_result({**RESULT, "verdict": "needs_caseworker"})
    assert webmap.client_state(rf) == "check"
    assert webmap.client_state(webmap.to_check_result({**RESULT, "verdict": "meets"})) == "ready"
    assert webmap.client_state(None) is None


def test_short_org_keeps_full_names_for_gps_and_councils():
    assert webmap.short_org("Elm Grove Medical Practice") == "Elm Grove Medical Practice"
    assert webmap.short_org("Bath and Northeast Somerset Council") == "Bath and Northeast Somerset Council"
    assert webmap.short_org("Riverside Domestic Abuse Service") == "Riverside"
    assert webmap.short_org("Women's Aid") == "Women's Aid"


def test_case_and_documents_from_store():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider", firm_name="Hartley & Webb Solicitors", ask_label="Letter from your GP")
    store.create_client_link(c["id"], 7)
    d1 = store.add_document(c["id"], "refuge.txt", "client", None, None, "text one", pages=[{"filename": "refuge.jpg", "contentType": "image/jpeg"}, {"filename": "refuge (2).jpg", "contentType": "image/jpeg"}])
    store.set_document_result(d1["id"], RESULT)
    d2 = store.add_document(c["id"], "refuge-v2.txt", "provider", None, None, "text two", replaces=d1["id"])
    store.set_document_result(d2["id"], {**RESULT, "verdict": "meets", "elements": [{**RESULT["elements"][1]}], "flags": []})
    out = webmap.case_with_documents(store, store.get_case(c["id"]))
    case, docs = out["case"], out["documents"]
    assert set(case) == {"id", "ref", "firm", "applicantName", "otherPartyName", "caseType", "createdAt", "clientToken", "tokenExpiresAt",
                         "askLabel", "documentIds", "selectedDocumentIds", "selectionTouched", "submittedAt", "submittedDocumentIds", "submitReason", "decision"}
    assert case["clientToken"] and case["tokenExpiresAt"] and case["askLabel"] == "Letter from your GP"
    assert case["selectedDocumentIds"] == [d2["id"]] and case["selectionTouched"] is False   # default: latest passing document
    assert set(docs[0]) == {"id", "caseId", "pages", "text", "uploadedBy", "uploadedAt", "result"}
    assert docs[0]["pages"][1]["filename"] == "refuge (2).jpg" and docs[0]["text"] == "text one"
    store.set_selection(c["id"], [d1["id"]], "provider")
    case2 = webmap.case_with_documents(store, store.get_case(c["id"]))["case"]
    assert case2["selectedDocumentIds"] == [d1["id"]] and case2["selectionTouched"] is True
    sub = store.create_submission(c["id"], [d2["id"]], None, None, "provider")
    store.add_decision(sub["id"], "Priya", "accept", "")
    case3 = webmap.case_with_documents(store, store.get_case(c["id"]))["case"]
    assert case3["submittedAt"] and case3["submittedDocumentIds"] == [d2["id"]]
    assert case3["decision"]["action"] == "accept" and case3["decision"]["agreedWithTool"] is True
    assert "Case: " + case3["ref"] in webmap.verification_summary(case3, docs)


def test_quotes_are_anchored_to_the_document_text_for_highlighting():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider")
    text = "Home Office \u2013 UK Visas and Immigration\n\nDear Jane,\n\nLeave granted.\n\nUK Visas and Immigration\nOn behalf of the Secretary of State"
    d = store.add_document(c["id"], "ho.txt", "provider", None, None, text)
    res = {**RESULT, "verdict": "meets", "elements": [{**RESULT["elements"][1], "element_id": "from_home_office",
           "quote": "Home Office - UK Visas and Immigration\n\nOn behalf of the Secretary of State"}], "flags": ["quote_multi_span"]}
    store.set_document_result(d["id"], res)
    doc = webmap.to_document(store, store.get_document(d["id"]))
    q = doc["result"]["elements"][0]["quote"]
    assert q in doc["text"] and q == "Home Office \u2013 UK Visas and Immigration"


def test_missing_element_gets_the_problem_wording_from_its_explanation():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", None, "Child arrangements", "provider")
    text = "In my reasonable professional judgement Jane Doe is a victim.\n\nThe matter I have relied upon to support that judgements are: Victim testimony and referral.\n\nWe have provided support."
    d = store.add_document(c["id"], "s.txt", "provider", None, None, text)
    res = {**RESULT, "elements": [{**RESULT["elements"][0], "element_id": "specific_matters", "quote": None,
           "reasoning": "\u201cVictim testimony and referral\u201d gives only sources of information, not the specific matters relied on."}], "flags": []}
    store.set_document_result(d["id"], res)
    doc = webmap.to_document(store, store.get_document(d["id"]))
    e = doc["result"]["elements"][0]
    assert e["status"] == "not_met" and e["quote"] == "Victim testimony and referral" and e["quote"] in doc["text"]
