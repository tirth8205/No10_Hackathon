"""The /web layer must return exactly the shapes in web/src/lib/types.ts."""
import json
import os
import tempfile

import pytest

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
    assert set(r) == {"matchedPara", "outcome", "reason", "nameCheck", "elements", "flags", "authorOrg", "shortOrg", "authorName", "authorRole",
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
                         "askLabel", "documentIds", "selectedDocumentIds", "selectionTouched", "submittedAt", "submittedDocumentIds", "submitReason", "decision",
                         "submissionId"}
    assert case["clientToken"] and case["tokenExpiresAt"] and case["askLabel"] == "Letter from your GP"
    assert case["submissionId"] is None and "laaCheck" not in case          # nothing submitted yet; the LAA's check never crosses back to link 1
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
    assert case3["submissionId"] == sub["id"] and "laaCheck" not in case3   # the frontend downloads /web/submissions/{submissionId}/pack.zip
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


def test_verification_links_are_http_only():
    from engine.models import VerificationCheck

    assert VerificationCheck(id="x", label="x", status="unknown", detail="d", link="javascript:alert(1)").link is None
    assert VerificationCheck(id="x", label="x", status="unknown", detail="d", link=" https://example.org/a ").link == "https://example.org/a"


# --------------------------------------------------------------------------- #
# roles: each party gets only what crosses its link
# --------------------------------------------------------------------------- #
def test_client_result_is_reduced_to_plain_words():
    r = webmap.to_check_result({**RESULT, "client_message": "This document may need a little more detail."}, role="client")
    assert set(r) == {"matchedPara", "outcome", "reason", "nameCheck", "elements", "shortOrg", "authorName", "letterDate", "rulesVersion", "checkedAt"}
    assert not (set(r) & webmap.CLIENT_HIDDEN_RESULT_KEYS)
    assert r["outcome"] == "fail" and r["matchedPara"] == "18" and r["shortOrg"] == "Brookfield" and r["letterDate"] == "2026-09-28"
    assert r["reason"] == "This document may need a little more detail."     # the client message, never the provider summary
    assert r["authorName"] is None                                           # the classifier knew "John Smith"; the client's phone does not
    assert [set(e) for e in r["elements"]] == [{"key", "status", "clientHint", "fix"}] * 2
    assert r["elements"][0] == {"key": "perpetrator_named", "status": "not_met", "clientHint": "name the person you needed to get away from", "fix": "Name the other party."}
    assert webmap.to_check_result(RESULT) == webmap.to_check_result(RESULT, role="provider") == webmap.to_check_result(RESULT, role="caseworker")
    err = webmap.error_result("KeyError: x", role="client")
    assert err["reason"] == webmap.CLIENT_ERROR_MESSAGE and "KeyError" not in str(err) and not (set(err) & webmap.CLIENT_HIDDEN_RESULT_KEYS)
    with pytest.raises(ValueError):
        webmap.to_check_result(RESULT, role="auditor")


def test_client_document_has_no_text_and_the_caseworker_case_has_no_link_1_fields():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider", firm_name="Hartley & Webb Solicitors")
    store.create_client_link(c["id"], 7)
    d = store.add_document(c["id"], "refuge.txt", "client", None, None, "on 28th September 2026 she was refused")
    store.set_document_result(d["id"], RESULT)
    client_doc = webmap.to_document(store, store.get_document(d["id"]), role="client")
    assert set(client_doc) == {"id", "caseId", "pages", "uploadedBy", "uploadedAt", "result"}
    assert not (set(client_doc) & webmap.CLIENT_HIDDEN_DOCUMENT_KEYS)
    assert webmap.to_document(store, store.get_document(d["id"]))["text"] == "on 28th September 2026 she was refused"
    sub = store.create_submission(c["id"], [d["id"]], None, "reason", "provider")
    docs = [webmap.to_document(store, store.get_document(d["id"]))]
    cw = webmap.to_case(store, store.get_case(c["id"]), docs, role="caseworker")
    assert not (set(cw) & webmap.CASEWORKER_HIDDEN_CASE_KEYS)
    assert cw["ref"] == sub["laa_ref"] and cw["submissionId"] == sub["id"] and cw["laaCheck"] == {"done": False, "differences": 0}
    prov = webmap.to_case(store, store.get_case(c["id"]), docs)
    assert prov["ref"] == c["ref"] and prov["clientToken"] and "laaCheck" not in prov


def test_submission_with_documents_is_the_frozen_pack():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider", firm_name="Hartley & Webb Solicitors")
    text = "Dear Jane Doe, on 28th September 2026 you were refused admission to the refuge."
    d = store.add_document(c["id"], "refuge.txt", "provider", "18", None, text, pages=[{"filename": "refuge.pdf", "contentType": "application/pdf"}])
    store.set_document_result(d["id"], RESULT)
    sub = store.create_submission(c["id"], [d["id"]], None, "reason", "provider")
    snap = sub["snapshot"]["documents"][0]
    assert snap["snapshot_text"] == text and snap["uploaded_by"] == "provider" and snap["pages"][0]["filename"] == "refuge.pdf"

    # the live case moves on: new names, a new result, the text purged
    store.update_case(c["id"], applicant_name="Someone Else", other_party_name=None)
    store.set_document_result(d["id"], {**RESULT, "verdict": "meets", "elements": [RESULT["elements"][1]], "flags": []})
    store.purge_case_documents(c["id"], "provider")
    assert store.document_text(d["id"]) is None

    out = webmap.submission_with_documents(store, store.get_submission(sub["id"]), "caseworker", base_url="http://x")
    case, docs = out["case"], out["documents"]
    assert set(case) == {"id", "ref", "firm", "applicantName", "otherPartyName", "caseType", "createdAt", "documentIds", "submittedAt",
                         "submittedDocumentIds", "submitReason", "decision", "submissionId", "laaCheck"}
    assert case["id"] == c["id"] and case["ref"] == sub["laa_ref"] and case["submissionId"] == sub["id"]
    assert case["applicantName"] == "Jane Doe" and case["otherPartyName"] == "John Doe" and case["firm"] == "Hartley & Webb Solicitors"
    assert case["submitReason"] == "reason" and case["decision"] is None and case["laaCheck"] == {"done": False, "differences": 0}
    assert len(docs) == 1 and docs[0]["text"] == text and docs[0]["caseId"] == c["id"] and docs[0]["pages"] == [{"filename": "refuge.pdf", "contentType": "application/pdf"}]
    assert docs[0]["result"]["outcome"] == "fail" and [e["status"] for e in docs[0]["result"]["elements"]] == ["not_met", "met"]
    assert docs[0]["result"]["elements"][1]["quote"] == "on 28th September 2026"

    store.set_laa_check(sub["id"], {"documents": [], "checked_at": "now"}, [{"document_id": d["id"], "element_id": "x", "provider": "missing", "laa": "included"},
                                                                             {"document_id": d["id"], "element_id": None, "provider": "needs_change", "laa": "meets"}])
    store.add_decision(sub["id"], "Priya", "return", "Name the other party")
    case2 = webmap.submission_with_documents(store, store.get_submission(sub["id"]), "caseworker")["case"]
    assert case2["laaCheck"] == {"done": True, "differences": 2} and case2["decision"]["action"] == "return"
    assert "Case: " + sub["laa_ref"] in webmap.verification_summary(case2, docs)


def test_snapshot_without_snapshot_text_falls_back_to_the_held_text():
    """Submissions made before snapshot_text existed (older demo databases)."""
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider")
    d = store.add_document(c["id"], "refuge.txt", "client", None, None, "held text")
    store.set_document_result(d["id"], RESULT)
    sub = store.create_submission(c["id"], [d["id"]], None, None, "provider")
    for k in ("snapshot_text", "uploaded_by", "uploaded_at", "pages"):
        sub["snapshot"]["documents"][0].pop(k)
    store._exec("UPDATE submissions SET snapshot_json=? WHERE id=?", (json.dumps(sub["snapshot"]), sub["id"]))
    doc = webmap.submission_with_documents(store, store.get_submission(sub["id"]))["documents"][0]
    assert doc["text"] == "held text" and doc["uploadedBy"] == "client" and doc["pages"][0]["filename"] == "refuge.txt"


# --------------------------------------------------------------------------- #
# the text TTL
# --------------------------------------------------------------------------- #
def test_document_text_expires_after_the_ttl_and_only_the_snapshot_keeps_it():
    from app.store import iso_ago

    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    store.text_ttl_seconds = store.docs.ttl = 600
    c = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider")
    d = store.add_document(c["id"], "refuge.txt", "provider", None, b"bytes", "the text")
    store.set_document_result(d["id"], RESULT)
    sub = store.create_submission(c["id"], [d["id"]], None, None, "provider")
    assert store.document_text(d["id"]) == "the text" and store.get_document(d["id"])["text_available"] is True

    store._exec("UPDATE documents SET uploaded_at=? WHERE id=?", (iso_ago(601), d["id"]))
    assert store.document_text(d["id"]) is None                                   # expired on access
    assert store._one("SELECT text, purged FROM documents WHERE id=?", (d["id"],)) == {"text": None, "purged": 0}
    assert store.docs.get(d["id"]) is None and store.get_document(d["id"])["text_available"] is False
    assert store.get_document(d["id"])["result"]["verdict"] == "needs_change"      # the result stays
    assert store.get_submission(sub["id"])["snapshot"]["documents"][0]["snapshot_text"] == "the text"

    fresh = store.add_document(c["id"], "later.txt", "provider", None, None, "fresh text")
    assert store.sweep_expired_text() == 0 and store.document_text(fresh["id"]) == "fresh text"
    store.docs.sweep()                                                            # the memory sweep also runs the SQLite sweep
    store._exec("UPDATE documents SET uploaded_at=? WHERE id=?", (iso_ago(601), fresh["id"]))
    store.docs.sweep()
    assert store._one("SELECT text FROM documents WHERE id=?", (fresh["id"],))["text"] is None
