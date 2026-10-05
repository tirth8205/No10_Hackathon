"""Text extraction (PDF / DOCX / image) and annotation, offline: no API key needed.

The fixtures under tests/fixtures/ are built by tests/fixtures/make_fixtures.py
(regenerated here if missing). The /web API tests run the FastAPI app in-process with
GC_LLM=offline and a throw-away SQLite file; the env is set BEFORE app is imported, and
engine.config.settings is patched too in case an earlier test module imported it first.
"""
import os
import tempfile
from pathlib import Path

_DB = os.path.join(tempfile.mkdtemp(prefix="gc-test-"), "api.sqlite3")
os.environ["GC_LLM"] = "offline"
os.environ["GC_CACHE"] = "off"
os.environ["GC_DB_PATH"] = _DB

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from engine.config import settings  # noqa: E402

settings.llm, settings.cache, settings.db_path = "offline", "off", Path(_DB)

from app import core  # noqa: E402
from app.main import app  # noqa: E402
from engine import outputs  # noqa: E402
from engine.ingest import Ingested, UnsupportedFile, ingest  # noqa: E402
from engine.llm import OfflineLLM  # noqa: E402
from engine.models import FLAG_ILLEGIBLE, Application  # noqa: E402
from engine.pipeline import check_document  # noqa: E402
from engine.rules import load_rules  # noqa: E402
from engine.verify import normalise, spans  # noqa: E402
from tests.fixtures import make_fixtures as fx  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
RULES = load_rules()
JANE = Application(applicant_name="Jane Doe", other_party_name="John Doe")


def _fixture(name: str) -> bytes:
    path = FIX / name
    if not all((FIX / n).exists() for n in fx.ALL):
        fx.build(FIX)
    return path.read_bytes()


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(core.state, "llm", OfflineLLM())
    with TestClient(app) as client:  # background checks finish before each response returns
        yield client


def _new_case(api, applicant="Jane Doe", other="John Doe") -> dict:
    r = api.post("/web/cases", json={"applicantName": applicant, "otherPartyName": other})
    assert r.status_code == 201, r.text
    return r.json()["case"]


# --------------------------------------------------------------------------- #
# ingest()
# --------------------------------------------------------------------------- #
def test_pdf_with_text_layer_is_extracted_not_transcribed():
    ing = ingest(_fixture(fx.PDF_NAME), "refuge-letter.pdf")
    assert ing.kind == "pdf" and ing.pages == 1
    assert ing.needs_transcription is False and ing.data is None and ing.media_type is None
    for words in ("Name of perpetrator: John Doe", "refused admission to a refuge", "28th September 2026", "Women’s Aid"):
        assert words in ing.text, words


def test_png_photo_is_held_for_transcription():
    data = _fixture(fx.PNG_NAME)
    ing = ingest(data, "IMG_0001.PNG")  # extension case does not matter
    assert ing.kind == "image" and ing.needs_transcription is True
    assert ing.media_type == "image/png" and ing.data == data and ing.text == ""


def test_docx_paragraphs_are_extracted():
    ing = ingest(_fixture(fx.DOCX_NAME), "support-letter.docx")
    assert ing.kind == "docx" and ing.needs_transcription is False
    expected = [p.strip() for p in fx.p17_corrected_text().split("\n") if p.strip()]
    assert ing.text.split("\n") == expected


def test_unsupported_extension_is_refused():
    with pytest.raises(UnsupportedFile):
        ingest(b"abc", "letter.xyz")
    with pytest.raises(UnsupportedFile):
        ingest(b"abc", "letter.exe")
    # text-like and extensionless files are read as text
    assert ingest("Dear Jane\n".encode(), "letter.txt").text == "Dear Jane\n"
    assert ingest(b"Dear Jane", "README").kind == "text"


# --------------------------------------------------------------------------- #
# check_document(): the engine on files
# --------------------------------------------------------------------------- #
def test_photo_the_model_cannot_read_goes_to_a_caseworker_as_illegible():
    res = asyncio.run(check_document(_fixture(fx.PNG_NAME), "photo.png", JANE, rules=RULES, llm=OfflineLLM(), votes=1, claimed_para="11"))
    assert res.verdict == "needs_caseworker"
    assert res.flags == [FLAG_ILLEGIBLE]
    assert res.client_message == outputs.CLIENT_ILLEGIBLE
    assert "another photo" in res.client_message
    assert "rejected" not in res.client_message.lower() and "fail" not in res.client_message.lower()
    assert res.elements == []
    assert res.paragraph is None and res.rule_id is None  # nothing was assessed, so no paragraph is reported


def test_pdf_letter_is_checked_with_verified_quotes_that_land_in_the_text():
    data = _fixture(fx.PDF_NAME)
    text = ingest(data, "refuge-letter.pdf").text
    res = asyncio.run(check_document(data, "refuge-letter.pdf", JANE, rules=RULES, llm=OfflineLLM(), votes=1, claimed_para="18"))
    # the same letter as text meets paragraph 18 (test_engine); extracting it from a PDF must not change that
    assert res.verdict == "meets", (res.verdict, res.flags, [(e.element_id, e.status) for e in res.elements])
    assert res.paragraph == "18" and res.rule_id == "sch1_p18_refuge_refusal"
    assert res.flags == [] and res.request_letter is None
    included = [e for e in res.elements if e.status == "included"]
    assert len(included) == len(res.elements) == len(RULES.get("sch1_p18_refuge_refusal").elements)
    assert all(e.quote and e.quote_verified for e in included), [(e.element_id, e.quote) for e in included]
    for e in included:
        found = spans(e.quote, text)
        assert found, e.quote
        for a, b in found:
            assert 0 <= a < b <= len(text)
        assert normalise(" ".join(text[a:b] for a, b in found)) == normalise(e.quote)


def test_pdf_letter_text_from_the_check_matches_the_ingested_text():
    """The verdict is computed on the same text the UI will show for highlighting."""
    data = _fixture(fx.PDF_NAME)
    ing = ingest(data, "refuge-letter.pdf")
    res = asyncio.run(check_document(data, "refuge-letter.pdf", JANE, rules=RULES, llm=OfflineLLM(), votes=1, claimed_para="18"))
    for e in res.elements:
        if e.quote:
            assert e.quote in ing.text  # offline stub quotes whole sentences; they must be substrings


# --------------------------------------------------------------------------- #
# /web API: multi-page upload and the annotation contract
# --------------------------------------------------------------------------- #
def test_two_png_pages_upload_as_one_document_with_file_links(api):
    case = _new_case(api)
    p1, p2 = _fixture(fx.PNG_PAGES[0]), _fixture(fx.PNG_PAGES[1])
    r = api.post(f"/web/cases/{case['id']}/documents",
                 files=[("files", ("gp-letter-1.png", p1, "image/png")), ("files", ("gp-letter-2.png", p2, "image/png"))])
    assert r.status_code == 202, r.text
    doc = r.json()
    assert doc["caseId"] == case["id"] and doc["uploadedBy"] == "provider"
    assert [p["filename"] for p in doc["pages"]] == ["gp-letter-1.png", "gp-letter-2.png"]
    assert {p["contentType"] for p in doc["pages"]} == {"image/png"}
    assert all(p.get("url") for p in doc["pages"])
    for page, data in zip(doc["pages"], (p1, p2)):
        f = api.get(page["url"])
        assert f.status_code == 200, page["url"]
        assert f.headers["content-type"].startswith("image/png")
        assert f.content == data

    # the check has run (offline stub cannot read a photo): one document, not two
    got = api.get(f"/web/cases/{case['id']}/documents/{doc['id']}")
    assert got.status_code == 200
    d = got.json()
    assert len(d["pages"]) == 2
    case_docs = api.get(f"/web/cases/{case['id']}").json()["documents"]
    assert [x["id"] for x in case_docs] == [doc["id"]]
    assert d["result"] is not None
    assert d["result"]["outcome"] == "refer", d["result"]
    assert d["result"]["flags"] == ["Document could not be read"]
    assert d["result"]["matchedPara"] is None and d["result"]["elements"] == []
    assert "another photo" in d["result"]["reason"].lower() or "clearer copy" in d["result"]["reason"].lower(), d["result"]["reason"]
    assert d["text"] == ""


def test_txt_upload_quotes_are_substrings_of_the_document_text(api):
    """The contract web/src/lib/highlight.ts relies on: every quote is found with indexOf."""
    case = _new_case(api)
    letter = fx.p18_accepted_text().encode()
    r = api.post(f"/web/cases/{case['id']}/documents", files=[("files", ("refuge.txt", letter, "text/plain"))])
    assert r.status_code == 202, r.text
    doc_id = r.json()["id"]
    d = api.get(f"/web/cases/{case['id']}/documents/{doc_id}").json()
    assert d["pages"] == [{"filename": "refuge.txt", "contentType": "text/plain", "url": d["pages"][0]["url"]}]
    assert d["text"] == letter.decode()
    res = d["result"]
    assert res is not None and res["matchedPara"] == "18"
    assert res["outcome"] == "pass" and res["flags"] == [], res
    assert res["elements"] and all(e["status"] == "met" for e in res["elements"]), [(e["key"], e["status"]) for e in res["elements"]]
    for e in res["elements"]:
        assert e["quote"] and e["quote"] in d["text"], e


def test_docx_upload_through_the_api_is_read_as_text(api):
    case = _new_case(api, other="")
    r = api.post(f"/web/cases/{case['id']}/documents",
                 files=[("files", ("support-letter.docx", _fixture(fx.DOCX_NAME),
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))])
    assert r.status_code == 202, r.text
    d = api.get(f"/web/cases/{case['id']}/documents/{r.json()['id']}").json()
    assert d["text"] == ingest(_fixture(fx.DOCX_NAME), "support-letter.docx").text  # the UI annotates exactly what ingest() produced
    assert "regulation 33" in d["text"] and "Jane Doe" in d["text"]
    assert d["pages"][0]["contentType"].endswith("wordprocessingml.document")
    assert d["result"] is not None and d["result"]["outcome"] != "refer", d["result"]
    met = [e for e in d["result"]["elements"] if e["status"] == "met"]
    assert met
    for e in met:
        assert e["quote"] and e["quote"] in d["text"], e


def test_unsupported_upload_is_rejected_with_415(api):
    case = _new_case(api)
    r = api.post(f"/web/cases/{case['id']}/documents", files=[("files", ("letter.xyz", b"abc", "application/octet-stream"))])
    assert r.status_code == 415


def test_empty_document_is_reported_as_unreadable_not_as_wrong_type():
    import asyncio
    from engine.llm import OfflineLLM
    from engine.models import Application
    from engine.pipeline import check_text

    res = asyncio.run(check_text("", "empty.txt", Application(applicant_name="Jane Doe"), llm=OfflineLLM(), votes=1))
    assert res.verdict == "needs_caseworker" and "illegible" in res.flags and "another photo" in res.client_message
