"""Transcription and the end-to-end check with the real model.

Skipped unless OPENAI_API_KEY is set (engine.config loads .env). Runs with GC_CACHE=on,
so after the first run every call is served from demo/cache/ and reruns are free.
Live calls: 1 transcription of the single photo, 2 of the two pages, plus one classify
and k assessments per check.
"""
import os
import tempfile
from pathlib import Path

_DB = os.path.join(tempfile.mkdtemp(prefix="gc-live-"), "api.sqlite3")
os.environ.setdefault("GC_DB_PATH", _DB)

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from engine.config import settings  # noqa: E402

if "GC_DB_PATH" in os.environ and str(settings.db_path) != os.environ["GC_DB_PATH"]:
    settings.db_path = Path(os.environ["GC_DB_PATH"])

from app import core  # noqa: E402
from app.main import app  # noqa: E402
from engine.ingest import ingest  # noqa: E402
from engine.llm import get_llm  # noqa: E402
from engine.models import Application  # noqa: E402
from engine.pipeline import check_document  # noqa: E402
from engine.rules import load_rules  # noqa: E402
from tests.fixtures import make_fixtures as fx  # noqa: E402

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set; live model tests skipped")

FIX = Path(__file__).resolve().parent / "fixtures"
RULES = load_rules()


def _fixture(name: str) -> bytes:
    if not all((FIX / n).exists() for n in fx.ALL):
        fx.build(FIX)
    return (FIX / name).read_bytes()


@pytest.fixture
def llm():
    # CachedLLM(OpenAILLM): record on first run, replay after. Built per test because each
    # asyncio.run() (and the TestClient) uses its own event loop, and an AsyncOpenAI client's
    # pooled connection cannot be reused across loops.
    return get_llm("openai", "on")


@pytest.fixture
def api(monkeypatch, llm):
    monkeypatch.setitem(core.state, "llm", llm)
    with TestClient(app) as client:
        yield client


def test_model_transcribes_the_photo(llm):
    ing = ingest(_fixture(fx.PNG_NAME), "gp-letter.png")
    tr = asyncio.run(llm.transcribe(ing.data, ing.media_type))
    print("\nTRANSCRIPTION[:200] =", repr(tr.text[:200]))
    assert tr.legible, tr.notes
    assert "might be consistent" in tr.text
    assert "Jane Doe" in tr.text


def test_hedged_gp_photo_needs_a_change_on_the_judgement(llm):
    res = asyncio.run(check_document(_fixture(fx.PNG_NAME), "gp-letter.png", Application(applicant_name="Jane Doe"),
                                     rules=RULES, llm=llm, claimed_para="11"))
    assert res.verdict == "needs_change", (res.verdict, res.flags, [(e.element_id, e.status) for e in res.elements])
    assert res.paragraph == "11" and "hedge" in res.flags, res.flags
    judgement = next(e for e in res.elements if e.element_id == "consistent_with_domestic_abuse")
    assert judgement.status == "missing", judgement
    included = [e for e in res.elements if e.status == "included"]
    assert included and all(e.quote and e.quote_verified for e in included), [(e.element_id, e.quote) for e in included]
    assert res.request_letter and "paragraph 11" in res.request_letter
    assert "rejected" not in res.client_message.lower() and "fail" not in res.client_message.lower()


def test_two_page_photo_through_the_web_api(api):
    r = api.post("/web/cases", json={"applicantName": "Jane Doe", "otherPartyName": ""})
    case = r.json()["case"]
    p1, p2 = _fixture(fx.PNG_PAGES[0]), _fixture(fx.PNG_PAGES[1])
    r = api.post(f"/web/cases/{case['id']}/documents",
                 files=[("files", ("gp-letter-1.png", p1, "image/png")), ("files", ("gp-letter-2.png", p2, "image/png"))])
    assert r.status_code == 202, r.text
    doc_id = r.json()["id"]
    d = api.get(f"/web/cases/{case['id']}/documents/{doc_id}").json()
    assert [p["filename"] for p in d["pages"]] == ["gp-letter-1.png", "gp-letter-2.png"]
    for page, data in zip(d["pages"], (p1, p2)):
        f = api.get(page["url"])
        assert f.status_code == 200 and f.content == data, page
    # the transcription of both pages, in order, is what the UI annotates
    assert "regulation 33" in d["text"] and "might be consistent" in d["text"], d["text"]
    assert d["text"].index("regulation 33") < d["text"].index("might be consistent")
    res = d["result"]
    assert res is not None, d
    assert res["outcome"] == "fail" and res["matchedPara"] == "11", res
    assert "Hedged wording" in res["flags"], res["flags"]
    met = [e for e in res["elements"] if e["status"] == "met"]
    assert met, res["elements"]
    for e in met:
        assert e["quote"] and e["quote"] in d["text"], e
    judgement = next(e for e in res["elements"] if e["key"] == "consistent_with_domestic_abuse")
    assert judgement["status"] == "not_met" and judgement["quote"] is None, judgement
