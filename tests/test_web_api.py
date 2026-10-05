"""The /web API in-process: link 2 is the frozen pack, roles see only what crosses their link.

  1. /web submit schedules the LAA's independent check (app.core.laa_check), shown as case.laaCheck.
  2. The caseworker queue, review and decision come from the submission snapshot, one row per
     submission, each with its submissionId; a later re-check or purge changes nothing there.
  3. Roles: the caseworker never gets the client link, ask label, selection or the link-1 case ref;
     the client never gets the document text, quotes, reasoning, flags, names or verification.
  4. Extracted text expires with GC_DOC_TTL_MIN; the submission's snapshot_text is the only copy kept.
  5. GET /web/submissions/{id}/pack.zip: the submitted files (or their text) plus the summary.

GC_LLM=offline and a throw-away SQLite file are set BEFORE the app is imported; engine.config.settings
is patched too in case another test module imported it first (app.core.store is created once per process).
"""
import asyncio
import io
import os
import tempfile
import zipfile
from pathlib import Path

_DB = os.path.join(tempfile.mkdtemp(prefix="gc-webapi-"), "api.sqlite3")
os.environ["GC_LLM"] = "offline"
os.environ["GC_CACHE"] = "off"
os.environ.setdefault("GC_DB_PATH", _DB)
os.environ.setdefault("GC_DOC_TTL_MIN", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from engine.config import settings  # noqa: E402

settings.llm, settings.cache = "offline", "off"
if str(settings.db_path) != os.environ["GC_DB_PATH"]:
    settings.db_path = Path(os.environ["GC_DB_PATH"])

from app import core, webmap  # noqa: E402
from app.main import app  # noqa: E402
from app.store import iso_ago  # noqa: E402
from engine.llm import OfflineLLM  # noqa: E402
from tests.fixtures import make_fixtures as fx  # noqa: E402

TTL = 60  # one minute, whatever the process-wide setting was when app.core was first imported
LETTER = fx.p18_accepted_text()


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(core.state, "llm", OfflineLLM())
    monkeypatch.setattr(core.store, "text_ttl_seconds", TTL)
    monkeypatch.setattr(core.store.docs, "ttl", TTL)
    with TestClient(app) as client:  # background tasks (the check, the LAA check) finish before each response returns
        yield client


def _case(api, applicant="Jane Doe", other="John Doe") -> dict:
    r = api.post("/web/cases", json={"applicantName": applicant, "otherPartyName": other})
    assert r.status_code == 201, r.text
    return r.json()["case"]


def _upload(api, case: dict, text: str = LETTER, filename: str = "refuge.txt") -> dict:
    r = api.post(f"/web/cases/{case['id']}/documents", files=[("files", (filename, text.encode(), "text/plain"))])
    assert r.status_code == 202, r.text
    d = api.get(f"/web/cases/{case['id']}/documents/{r.json()['id']}").json()
    assert d["result"] is not None, d
    return d


def _submit(api, case: dict, doc_ids: list[str], reason: str | None = None) -> dict:
    r = api.post(f"/web/cases/{case['id']}/submit", json={"documentIds": doc_ids, "reason": reason})
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# 1. the LAA's independent check
# --------------------------------------------------------------------------- #
def test_web_submit_schedules_the_laa_independent_check(api):
    case = _case(api)
    doc = _upload(api, case)
    assert doc["result"]["outcome"] == "pass"
    out = _submit(api, case, [doc["id"]])
    sid = out["submissionId"]
    assert set(out) >= {"case", "documents", "summary", "filename", "submissionId"}

    s = api.get(f"/api/submissions/{sid}").json()  # the engine-shaped view of the same submission
    assert s["laa_check"] is not None, "the LAA check did not run"
    assert s["laa_check"]["documents"][0]["verdict"] == "meets" and s["laa_check"]["checked_at"]
    assert s["differences"] == []

    item = api.get(f"/web/queue/{sid}").json()
    assert item["case"]["submissionId"] == sid
    assert item["case"]["laaCheck"] == {"done": True, "differences": 0}


def test_laa_check_counts_element_and_verdict_differences(api):
    """The provider's stored result is doctored before submitting; the LAA re-check on the same text disagrees."""
    case = _case(api)
    doc = _upload(api, case)
    row = core.store.get_document(doc["id"])
    tampered = {**row["result"], "verdict": "needs_change",
                "elements": [{**e, "status": "missing", "quote": None} if i == 0 else e for i, e in enumerate(row["result"]["elements"])]}
    core.store.set_document_result(doc["id"], tampered)
    sid = _submit(api, case, [doc["id"]], reason="testing")["submissionId"]
    s = api.get(f"/api/submissions/{sid}").json()
    kinds = {(d["element_id"], d["provider"], d["laa"]) for d in s["differences"]}
    assert (tampered["elements"][0]["element_id"], "missing", "included") in kinds
    assert (None, "needs_change", "meets") in kinds
    assert api.get(f"/web/queue/{sid}").json()["case"]["laaCheck"] == {"done": True, "differences": len(s["differences"])}


def test_laa_check_records_a_document_whose_text_is_gone_as_an_error(api):
    case = _case(api)
    doc = _upload(api, case)
    sub = core.store.create_submission(case["id"], [doc["id"]], None, None, "provider")
    sub["snapshot"]["documents"][0]["snapshot_text"] = None  # nothing to check
    asyncio.run(core.laa_check(sub))
    s = core.store.get_submission(sub["id"])
    assert s["laa_check"]["documents"] == [{"document_id": doc["id"], "error": "text no longer held"}]
    assert s["differences"] == []


# --------------------------------------------------------------------------- #
# 2. the frozen snapshot
# --------------------------------------------------------------------------- #
def test_queue_shows_the_frozen_pack_not_the_live_case(api):
    case = _case(api)
    doc = _upload(api, case)
    sid = _submit(api, case, [doc["id"]])["submissionId"]

    # afterwards the solicitor renames the applicant (which re-checks every letter) and purges the text
    api.patch(f"/web/cases/{case['id']}", json={"applicantName": "Someone Else"})
    live = api.get(f"/web/cases/{case['id']}/documents/{doc['id']}").json()
    assert live["result"]["outcome"] != "pass", "the live re-check should now disagree with the frozen pack"
    assert api.post(f"/api/cases/{case['id']}/purge").status_code == 200
    assert api.get(f"/web/cases/{case['id']}/documents/{doc['id']}").json()["text"] == ""

    items = [i for i in api.get("/web/queue").json() if i["case"]["submissionId"] == sid]
    assert len(items) == 1
    item = items[0]
    assert item["case"]["applicantName"] == "Jane Doe"
    assert item["documents"][0]["text"] == LETTER                      # snapshot_text survives the purge
    assert item["documents"][0]["result"]["outcome"] == "pass"         # and the frozen checklist is unchanged
    assert item["documents"][0]["id"] == doc["id"] and item["documents"][0]["caseId"] == case["id"]
    assert all(e["quote"] in LETTER for e in item["documents"][0]["result"]["elements"] if e["quote"])


def test_queue_has_one_row_per_submission_and_review_accepts_either_id(api):
    case = _case(api)
    doc = _upload(api, case)
    sid1 = _submit(api, case, [doc["id"]])["submissionId"]
    sid2 = _submit(api, case, [doc["id"]], reason="resubmitted with the same letter")["submissionId"]
    assert sid1 != sid2

    rows = [i for i in api.get("/web/queue").json() if i["case"]["id"] == case["id"]]
    assert [r["case"]["submissionId"] for r in rows] == [sid1, sid2]  # oldest first within the same verdict band
    assert api.get(f"/web/queue/{sid1}").json()["case"]["submissionId"] == sid1
    assert api.get(f"/web/queue/{sid2}").json()["case"]["submissionId"] == sid2
    assert api.get(f"/web/queue/{case['id']}").json()["case"]["submissionId"] == sid2       # case id -> latest submitted
    assert api.get(f"/web/queue/{case['ref']}").json()["case"]["submissionId"] == sid2      # case ref too
    laa_ref = api.get(f"/api/submissions/{sid1}").json()["laa_ref"]
    assert api.get(f"/web/queue/{laa_ref}").json()["case"]["submissionId"] == sid1          # and the LAA reference
    assert api.get("/web/queue/nope").status_code == 404


def test_decision_acts_on_exactly_one_submission(api):
    case = _case(api)
    doc = _upload(api, case)
    sid1 = _submit(api, case, [doc["id"]])["submissionId"]
    sid2 = _submit(api, case, [doc["id"]], reason="again")["submissionId"]

    r = api.post(f"/web/queue/{case['id']}/decision", json={"action": "return", "note": "older one", "submissionId": sid1})
    assert r.status_code == 201, r.text
    d = r.json()
    assert set(d) == {"action", "note", "toolVerdict", "agreedWithTool", "at", "submissionId"}
    assert d["submissionId"] == sid1 and d["action"] == "return" and d["toolVerdict"] == "meets" and d["agreedWithTool"] is False
    assert api.get(f"/api/submissions/{sid1}").json()["status"] == "returned"
    assert api.get(f"/api/submissions/{sid2}").json()["status"] == "submitted"
    assert [i["case"]["submissionId"] for i in api.get("/web/queue").json() if i["case"]["id"] == case["id"]] == [sid2]

    # without submissionId: the case's latest submitted one
    d2 = api.post(f"/web/queue/{case['id']}/decision", json={"action": "accept", "note": ""}).json()
    assert d2["submissionId"] == sid2 and d2["agreedWithTool"] is True
    assert api.get(f"/web/queue/{sid1}").json()["case"]["decision"]["action"] == "return"
    assert api.get(f"/web/queue/{sid2}").json()["case"]["decision"]["action"] == "accept"
    assert api.get(f"/web/queue/{case['id']}").json()["case"]["submissionId"] == sid2  # a decided case can still be opened

    other = _case(api, applicant="Amira Khan", other="Tariq Khan")
    other_doc = _upload(api, other)
    other_sid = _submit(api, other, [other_doc["id"]])["submissionId"]
    assert api.post(f"/web/queue/{case['id']}/decision", json={"action": "accept", "submissionId": other_sid}).status_code == 409
    assert api.post(f"/web/queue/{case['id']}/decision", json={"action": "accept", "submissionId": "missing"}).status_code == 404


# --------------------------------------------------------------------------- #
# 3. role boundaries
# --------------------------------------------------------------------------- #
def test_caseworker_never_sees_link_1_fields(api):
    case = _case(api)
    doc = _upload(api, case)
    sid = _submit(api, case, [doc["id"]])["submissionId"]
    laa_ref = api.get(f"/api/submissions/{sid}").json()["laa_ref"]

    for item in (api.get(f"/web/queue/{sid}").json(), *[i for i in api.get("/web/queue").json() if i["case"]["submissionId"] == sid]):
        c = item["case"]
        assert not (set(c) & webmap.CASEWORKER_HIDDEN_CASE_KEYS), set(c) & webmap.CASEWORKER_HIDDEN_CASE_KEYS
        assert c["ref"] == laa_ref and c["ref"] != case["ref"]      # the LAA never sees the case reference
        assert c["applicantName"] == "Jane Doe" and c["otherPartyName"] == "John Doe" and c["firm"] == "Demo Family Law LLP"
        assert c["submittedDocumentIds"] == [doc["id"]] and c["documentIds"] == [doc["id"]] and c["decision"] is None
        d = item["documents"][0]
        assert d["text"] == LETTER                                    # the caseworker does see the pack in full
        assert "flags" in d["result"] and "verification" in d["result"] and d["result"]["elements"][0]["quote"]


def test_client_view_is_plain_words_only(api):
    case = _case(api)
    token = case["clientToken"]
    r = api.post(f"/web/client/{token}/upload", files=[("files", ("refuge.txt", LETTER.encode(), "text/plain"))])
    assert r.status_code == 202, r.text
    doc_id = r.json()["documentId"]

    view = api.get(f"/web/client/{token}").json()
    assert set(view) == {"firstName", "firmName", "askLabel", "linkExpiresAt", "latestDocument", "state"}
    assert view["firstName"] == "Jane" and view["state"] == "ready"
    poll = api.get(f"/web/client/{token}/documents/{doc_id}").json()
    assert set(poll) == {"document", "state"} and poll["state"] == "ready"

    provider_doc = api.get(f"/web/cases/{case['id']}/documents/{doc_id}").json()
    for d in (view["latestDocument"], poll["document"]):
        assert d["id"] == doc_id and d["uploadedBy"] == "client"
        assert not (set(d) & webmap.CLIENT_HIDDEN_DOCUMENT_KEYS)                   # no document text
        res = d["result"]
        assert set(res) == {"matchedPara", "outcome", "reason", "nameCheck", "elements", "shortOrg", "authorName", "letterDate", "rulesVersion", "checkedAt"}
        assert not (set(res) & webmap.CLIENT_HIDDEN_RESULT_KEYS)
        assert res["outcome"] == "pass" and res["matchedPara"] == "18"
        assert res["authorName"] is None
        assert res["reason"] != provider_doc["result"]["reason"]                   # not the provider summary
        assert res["reason"] == core.store.get_document(doc_id)["result"]["client_message"]
        for word in ("paragraph", "rejected", "fail", "requirement"):
            assert word not in res["reason"].lower(), res["reason"]
        assert res["elements"] and all(set(e) == {"key", "status", "clientHint", "fix"} for e in res["elements"])
        assert not any(set(e) & webmap.CLIENT_HIDDEN_ELEMENT_KEYS for e in res["elements"])
    # the solicitor's copy of the same document is the full one
    assert provider_doc["text"] == LETTER and provider_doc["result"]["elements"][0]["quote"] and "flags" in provider_doc["result"]


def test_client_sees_a_plain_message_when_the_check_failed(api):
    case = _case(api)
    token = case["clientToken"]
    r = api.post(f"/web/client/{token}/upload", files=[("files", ("refuge.txt", LETTER.encode(), "text/plain"))])
    doc_id = r.json()["documentId"]
    core.store.set_document_result(doc_id, None, "RuntimeError: boom")
    res = api.get(f"/web/client/{token}/documents/{doc_id}").json()["document"]["result"]
    assert res["outcome"] == "refer" and res["reason"] == webmap.CLIENT_ERROR_MESSAGE
    assert "boom" not in str(res) and not (set(res) & webmap.CLIENT_HIDDEN_RESULT_KEYS)
    provider = api.get(f"/web/cases/{case['id']}/documents/{doc_id}").json()["result"]
    assert "boom" in provider["reason"] and provider["flags"]


# --------------------------------------------------------------------------- #
# 4. the text TTL
# --------------------------------------------------------------------------- #
def test_document_text_expires_with_the_ttl_but_the_submitted_pack_keeps_it(api):
    case = _case(api)
    doc = _upload(api, case)
    sid = _submit(api, case, [doc["id"]])["submissionId"]
    assert api.get(f"/api/cases/{case['id']}/documents/{doc['id']}/text").text == LETTER

    core.store._exec("UPDATE documents SET uploaded_at=? WHERE id=?", (iso_ago(TTL * 5), doc["id"]))  # uploaded five TTLs ago
    assert api.get(f"/api/cases/{case['id']}/documents/{doc['id']}/text").status_code == 410
    assert api.get(f"/web/cases/{case['id']}/documents/{doc['id']}").json()["text"] == ""
    assert core.store._one("SELECT text FROM documents WHERE id=?", (doc["id"],))["text"] is None   # nulled in SQLite
    assert core.store.docs.get(doc["id"]) is None                                                  # and dropped from memory
    assert api.get(f"/api/cases/{case['id']}/documents/{doc['id']}").json()["text_available"] is False
    assert api.post(f"/api/cases/{case['id']}/documents/{doc['id']}/recheck").status_code == 410

    item = api.get(f"/web/queue/{sid}").json()
    assert item["documents"][0]["text"] == LETTER                                  # the pack the LAA received
    assert api.get(f"/api/submissions/{sid}").json()["snapshot"]["documents"][0]["text"] == LETTER
    assert api.get(f"/api/submissions/{sid}").json()["snapshot"]["documents"][0]["highlights"]


def test_fresh_text_is_kept_until_the_ttl(api):
    case = _case(api)
    doc = _upload(api, case)
    core.store._exec("UPDATE documents SET uploaded_at=? WHERE id=?", (iso_ago(TTL // 2), doc["id"]))
    assert core.store.sweep_expired_text() == 0
    assert api.get(f"/web/cases/{case['id']}/documents/{doc['id']}").json()["text"] == LETTER


# --------------------------------------------------------------------------- #
# 5. the pack download
# --------------------------------------------------------------------------- #
def _zip(r) -> dict[str, bytes]:
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        return {n: z.read(n) for n in z.namelist()}


def test_pack_zip_holds_the_submitted_files_and_the_summary(api):
    case = _case(api)
    doc = _upload(api, case)
    sid = _submit(api, case, [doc["id"]])["submissionId"]
    laa_ref = api.get(f"/api/submissions/{sid}").json()["laa_ref"]

    r = api.get(f"/web/submissions/{sid}/pack.zip")
    files = _zip(r)
    assert f"Gateway Check {laa_ref}.zip" in r.headers["content-disposition"]
    assert set(files) == {"refuge.txt", "verification-summary.txt"}
    assert files["refuge.txt"] == LETTER.encode()                                   # the uploaded file, still held
    summary = files["verification-summary.txt"].decode()
    assert f"Case: {laa_ref}" in summary and case["ref"] not in summary             # the LAA reference, not the case ref
    assert "Meets the requirements" in summary and "Client: Jane Doe" in summary
    assert set(_zip(api.get(f"/web/submissions/{case['id']}/pack.zip"))) == set(files)   # a case id resolves to its latest submission
    assert api.get("/web/submissions/nope/pack.zip").status_code == 404


def test_pack_zip_falls_back_to_the_frozen_text_once_the_file_is_gone(api):
    case = _case(api)
    doc = _upload(api, case)
    sid = _submit(api, case, [doc["id"]])["submissionId"]
    api.post(f"/api/cases/{case['id']}/purge")
    files = _zip(api.get(f"/web/submissions/{sid}/pack.zip"))
    assert set(files) == {"refuge.txt", "verification-summary.txt"}
    assert files["refuge.txt"].decode() == LETTER
