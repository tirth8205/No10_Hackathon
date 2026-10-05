"""The main journey through /web, in one process against the offline model and a throw-away database.

  link 1   solicitor creates the case and a client link -> the applicant uploads the demo support
           letter -> polls until the result is in (and sees plain words only) -> the solicitor sees
           the full result -> submits the pack
  link 2   the LAA's queue row is the frozen snapshot (a later name change on the case does not
           reach it), carries the submission id and the LAA reference and nothing from link 1 ->
           the pack downloads as a zip -> the decision is taken on that submission -> the queue
           empties -> the LAA's own independent check is reported on the review

GC_LLM=offline and a temp SQLite file are set BEFORE the app is imported. app.core.store is created
once per process, so when another test module imported the app first this module shares its
throw-away database; the fixture empties it so the queue really is "the queue".
TestClient runs BackgroundTasks synchronously, so the document check and the LAA check have
finished by the time each response returns.
"""
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

_DB = os.path.join(tempfile.mkdtemp(prefix="gc-journey-"), "api.sqlite3")
os.environ["GC_LLM"] = "offline"
os.environ["GC_CACHE"] = "off"
os.environ.setdefault("GC_DB_PATH", _DB)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from engine.config import settings  # noqa: E402

settings.llm, settings.cache = "offline", "off"
if str(settings.db_path) != os.environ["GC_DB_PATH"]:
    settings.db_path = Path(os.environ["GC_DB_PATH"])

from app import core, webmap  # noqa: E402
from app.main import app  # noqa: E402
from engine.llm import OfflineLLM  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LETTER_PATH = ROOT / "demo" / "files" / "case-a-support-letter-corrected.txt"
LETTER = LETTER_PATH.read_text()
TABLES = ("cases", "documents", "tracker_events", "evidence_requests", "client_links", "submissions", "decisions", "audit")


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(core.state, "llm", OfflineLLM())
    for table in TABLES:  # the store is process-wide: start from nothing, as /web/demo/reset does
        core.store._exec(f"DELETE FROM {table}")
    core.store.docs._items.clear()
    with TestClient(app) as client:
        yield client


def _poll(api, url: str, attempts: int = 20) -> dict:
    """GET until the document carries a result. The background check is synchronous under
    TestClient, so this returns on the first pass; the loop is the contract the UI relies on."""
    body = None
    for _ in range(attempts):
        r = api.get(url)
        assert r.status_code == 200, r.text
        body = r.json()
        if body["document"]["result"] is not None:
            return body
    raise AssertionError(f"no result after {attempts} polls: {body}")


def _legal_detail(blob: str) -> list[str]:
    """Words and passages the applicant must never be sent: document text, quotes, reasoning, names, flags."""
    sentences = [s.strip() for s in LETTER.replace("\n", " ").split(". ") if len(s.strip()) > 20]
    leaked = [s for s in sentences if s[:40].lower() in blob.lower()]
    for word in ("offline stub", "requirements included", "paragraph 14", "schedule 1", "John Doe", "quote", "explanation", "flags", "verification"):
        if word.lower() in blob.lower():
            leaked.append(word)
    return leaked


def test_main_journey_through_web(api):
    # ------------------------------------------------------------------ link 1: the solicitor and the applicant
    r = api.post("/web/cases", json={"applicantName": "Jane Doe", "otherPartyName": "John Doe", "caseType": "Child arrangements",
                                     "askLabel": "Letter from your support worker"})
    assert r.status_code == 201, r.text
    case = r.json()["case"]
    assert case["clientToken"] and case["submissionId"] is None and case["documentIds"] == []

    r = api.post(f"/web/cases/{case['id']}/client-link")
    assert r.status_code == 201, r.text
    link = r.json()
    token = link["clientToken"]
    assert token and token != case["clientToken"]  # a fresh link replaces the one made with the case
    assert api.get(f"/web/client/{case['clientToken']}").status_code == 404  # and the old one is revoked

    view = api.get(f"/web/client/{token}").json()
    assert view == {"firstName": "Jane", "firmName": "Demo Family Law", "askLabel": "Letter from your support worker",
                    "linkExpiresAt": link["tokenExpiresAt"], "latestDocument": None, "state": None}

    with LETTER_PATH.open("rb") as f:
        r = api.post(f"/web/client/{token}/upload", files=[("files", (LETTER_PATH.name, f, "text/plain"))])
    assert r.status_code == 202, r.text
    doc_id = r.json()["documentId"]
    assert r.json()["pages"] == 1

    polled = _poll(api, f"/web/client/{token}/documents/{doc_id}")
    assert polled["state"] == "ready"
    client_doc = polled["document"]
    client_res = client_doc["result"]
    assert client_doc["id"] == doc_id and client_doc["uploadedBy"] == "client"
    assert client_res["outcome"] == "pass" and client_res["matchedPara"]
    # the applicant gets plain words only: no document text, quotes, explanations, flags, names or verification
    assert not (set(client_doc) & webmap.CLIENT_HIDDEN_DOCUMENT_KEYS)
    assert not (set(client_res) & webmap.CLIENT_HIDDEN_RESULT_KEYS)
    assert client_res["elements"] and all(set(e) == {"key", "status", "clientHint", "fix"} for e in client_res["elements"])
    assert not any(set(e) & webmap.CLIENT_HIDDEN_ELEMENT_KEYS for e in client_res["elements"])
    assert client_res["authorName"] is None
    assert client_res["reason"] == "Thank you. This document looks complete. Your solicitor will check it."
    view = api.get(f"/web/client/{token}").json()
    assert view["state"] == "ready" and view["latestDocument"]["id"] == doc_id
    for blob in (json.dumps(polled), json.dumps(view)):
        assert _legal_detail(blob) == [], _legal_detail(blob)
        assert case["ref"] not in blob  # the case reference stays with the solicitor

    # the solicitor sees everything
    r = api.get(f"/web/cases/{case['id']}")
    assert r.status_code == 200, r.text
    full = r.json()
    assert full["case"]["documentIds"] == [doc_id] and full["case"]["selectedDocumentIds"] == [doc_id]  # the passing letter is selected by default
    doc = full["documents"][0]
    assert doc["id"] == doc_id and doc["text"] == LETTER and doc["uploadedBy"] == "client"
    res = doc["result"]
    assert res["outcome"] == "pass" and res["matchedPara"] == client_res["matchedPara"]
    assert {"flags", "verification", "agreement", "authorOrg", "victimName", "otherPartyName"} <= set(res)
    assert res["reason"] != client_res["reason"] and "requirements included" in res["reason"]
    assert res["agreement"] == "3 of 3 checks agreed"
    for e in res["elements"]:
        assert set(e) == {"key", "label", "status", "quote", "explanation", "fix", "clientHint"}
        assert e["status"] == "met" and e["quote"] and e["quote"] in LETTER and e["explanation"]
    assert res["victimName"] == "Jane Doe"

    # ------------------------------------------------------------------ submit: the pack is frozen, the LAA re-checks it
    r = api.post(f"/web/cases/{case['id']}/submit", json={"documentIds": [doc_id], "reason": None})
    assert r.status_code == 201, r.text
    pack = r.json()
    assert set(pack) == {"case", "documents", "summary", "filename", "submissionId"}
    sid = pack["submissionId"]
    assert sid and pack["case"]["submissionId"] == sid           # the frontend downloads /web/submissions/{case.submissionId}/pack.zip
    assert pack["case"]["submittedDocumentIds"] == [doc_id] and pack["case"]["submittedAt"]
    assert "laaCheck" not in pack["case"]                          # the LAA's own check never crosses back to link 1
    assert [d["id"] for d in pack["documents"]] == [doc_id]
    assert f"Case: {case['ref']}" in pack["summary"] and "Client: Jane Doe" in pack["summary"]
    assert api.get(f"/web/cases/{case['id']}").json()["case"]["submissionId"] == sid

    engine_view = api.get(f"/api/submissions/{sid}").json()
    laa_ref = engine_view["laa_ref"]
    assert laa_ref and laa_ref != case["ref"]
    assert engine_view["laa_check"] is not None and engine_view["laa_check"]["documents"][0]["verdict"] == "meets"
    assert engine_view["differences"] == []

    # ------------------------------------------------------------------ link 2: the queue row is the snapshot, not the live case
    r = api.patch(f"/web/cases/{case['id']}", json={"applicantName": "Someone Else"})
    assert r.status_code == 200, r.text
    assert r.json()["case"]["applicantName"] == "Someone Else"
    live = api.get(f"/web/cases/{case['id']}/documents/{doc_id}").json()
    assert live["result"]["outcome"] != "pass"                     # the live re-check against the new name disagrees

    queue = api.get("/web/queue").json()
    assert [i["case"]["submissionId"] for i in queue] == [sid]
    review = api.get(f"/web/queue/{sid}").json()
    for item in (queue[0], review):
        c = item["case"]
        assert c["submissionId"] == sid
        assert c["ref"] == laa_ref and c["ref"] != case["ref"]
        assert c["applicantName"] == "Jane Doe" and c["otherPartyName"] == "John Doe"   # names as submitted
        assert "clientToken" not in c and not (set(c) & webmap.CASEWORKER_HIDDEN_CASE_KEYS)
        assert c["id"] == case["id"] and c["firm"] == "Demo Family Law LLP" and c["decision"] is None
        assert c["laaCheck"] == {"done": True, "differences": 0}
        d = item["documents"][0]
        assert d["id"] == doc_id and d["text"] == LETTER
        assert d["result"]["outcome"] == "pass"                       # the frozen checklist, not the live re-check
        assert all(e["quote"] in LETTER for e in d["result"]["elements"])
    assert api.get(f"/web/queue/{laa_ref}").json()["case"]["submissionId"] == sid
    assert api.get(f"/web/queue/{case['id']}").json()["case"]["submissionId"] == sid

    # ------------------------------------------------------------------ the pack as the LAA received it
    r = api.get(f"/web/submissions/{sid}/pack.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert f'filename="Gateway Check {laa_ref}.zip"' in r.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names = z.namelist()
        assert len(names) >= 2 and "verification-summary.txt" in names and LETTER_PATH.name in names
        assert z.read(LETTER_PATH.name).decode() == LETTER
        summary = z.read("verification-summary.txt").decode()
    assert f"Case: {laa_ref}" in summary and case["ref"] not in summary
    assert "Client: Jane Doe" in summary and "Someone Else" not in summary
    assert "Meets the requirements" in summary

    # ------------------------------------------------------------------ the decision, on exactly this submission
    r = api.post(f"/web/queue/{sid}/decision", json={"action": "accept", "note": "Letter meets paragraph 14.", "submissionId": sid})
    assert r.status_code == 201, r.text
    decision = r.json()
    assert decision["submissionId"] == sid and decision["action"] == "accept"
    assert decision["toolVerdict"] == "meets" and decision["agreedWithTool"] is True

    assert api.get("/web/queue").json() == []
    review = api.get(f"/web/queue/{sid}").json()
    assert review["case"]["decision"]["action"] == "accept" and review["case"]["decision"]["note"] == "Letter meets paragraph 14."
    assert review["case"]["laaCheck"] == {"done": True, "differences": 0}
    assert review["case"]["applicantName"] == "Jane Doe"
    assert api.get(f"/api/submissions/{sid}").json()["status"] == "accepted"

    # the solicitor sees the outcome on the case; the applicant still sees nothing of the LAA
    solicitor = api.get(f"/web/cases/{case['id']}").json()["case"]
    assert solicitor["decision"]["action"] == "accept" and solicitor["submissionId"] == sid
    view = api.get(f"/web/client/{token}").json()
    assert _legal_detail(json.dumps(view)) == [] and "accept" not in json.dumps(view).lower()


def test_decision_without_submission_id_still_resolves_the_case(api):
    """A client that only knows the case id (or ref) decides its latest submitted submission."""
    case = api.post("/web/cases", json={"applicantName": "Jane Doe", "otherPartyName": "John Doe"}).json()["case"]
    r = api.post(f"/web/cases/{case['id']}/documents", files=[("files", (LETTER_PATH.name, LETTER.encode(), "text/plain"))])
    doc_id = r.json()["id"]
    sid = api.post(f"/web/cases/{case['id']}/submit", json={"documentIds": [doc_id]}).json()["submissionId"]
    d = api.post(f"/web/queue/{case['ref']}/decision", json={"action": "refer", "note": "check the organisation"}).json()
    assert d["submissionId"] == sid and d["agreedWithTool"] is False
    assert api.get("/web/queue").json() == []
