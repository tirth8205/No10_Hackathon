"""Majority voting over k model assessments and per-vote record/replay.

Covers engine/pipeline._votes, engine/aggregate.majority and engine/llm.CachedLLM:

  * a failed vote is never dropped: it counts as "unclear" for every element, so one
    surviving vote out of three cannot decide on its own;
  * fewer than ceil(k/2) completed votes routes the document to a caseworker with the
    model_error flag and a summary saying the check could not be completed reliably;
  * each vote is cached under its own index, so a replay returns the same k distinct
    answers the live run produced, not one answer k times.

Everything here runs offline against a scripted fake model; the verification checks
(author and organisation look-ups) are stubbed out because they are not under test.
"""
import asyncio

import pytest

from engine import aggregate
from engine.llm import CachedLLM, OfflineLLM, RefusalError
from engine.models import (
    FLAG_MODEL_ERROR,
    FLAG_REFUSAL,
    FLAG_VOTE_DISAGREEMENT,
    Application,
    Assessment,
    Classification,
    ClassifyResponse,
    ElementAssessment,
    Parties,
    Transcription,
)
from engine.pipeline import check_text, quorum
from engine.rules import load_rules

RULES = load_rules()
RULE = RULES.get("sch1_p18_refuge_refusal")
APP = Application(applicant_name="Jane Doe", other_party_name="John Doe")
TEXT = (
    "Women's Aid Refuge Service\n\nDear Sir or Madam,\n\nRe: Jane Doe\n\n"
    "I can confirm that Jane Doe sought admission to our refuge on 3 March 2026 because of allegations of domestic abuse by John Doe, her former partner. "
    "We were unable to offer Jane Doe a place on 3 March 2026 because the refuge was full.\n\n"
    "Yours faithfully,\nA Smith\nRefuge Manager\nWomen's Aid Refuge Service"
)
# one verbatim passage per element, so an "included" vote verifies and the verdict can be "meets"
QUOTES = {
    "organisation_identified": "Women's Aid Refuge Service",
    "perpetrator_named": "domestic abuse by John Doe, her former partner",
    "victim_named": "Jane Doe sought admission to our refuge",
    "refusal_date": "We were unable to offer Jane Doe a place on 3 March 2026",
    "sought_because_of_abuse_by_other_party": "sought admission to our refuge on 3 March 2026 because of allegations of domestic abuse by John Doe",
}
assert set(QUOTES) == {e.id for e in RULE.elements}


@pytest.fixture(autouse=True)
def no_verification_lookups(monkeypatch):
    async def none(*args, **kwargs):
        return []

    monkeypatch.setattr("engine.pipeline.verify_document", none)


def vote(missing: tuple[str, ...] = ()) -> Assessment:
    return Assessment(
        elements=[
            ElementAssessment(element_id=eid, status="missing" if eid in missing else "included", quote=None if eid in missing else QUOTES[eid],
                              reasoning="fake", fix="Add it." if eid in missing else None)
            for eid in QUOTES
        ],
        hedging_detected=False,
        injection_detected=False,
    )


class FakeLLM:
    """Scripted model: answer i is returned for vote index i; an exception in the script is raised for that vote."""

    name = "fake"

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[int] = []

    async def classify(self, doc_text, rules):
        return ClassifyResponse(
            classification=Classification(rule_id=RULE.id, confidence="high", document_kind="letter", language="en", rationale="fake",
                                          author_name="A Smith", author_org="Women's Aid Refuge Service"),
            parties=Parties(victim_name="Jane Doe", other_party_name="John Doe"),
        )

    async def assess(self, doc_text, rule, applicant, other_party, hedge_terms, application_date=None, *, vote=0):
        self.calls.append(vote)
        answer = self.script[vote]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    async def transcribe(self, data, media_type):
        return Transcription(text="", legible=False)


def run(llm, votes=3):
    return asyncio.run(check_text(TEXT, "refuge.txt", APP, rules=RULES, llm=llm, votes=votes, claimed_para="18"))


def element(result_or_elements, eid):
    elements = getattr(result_or_elements, "elements", result_or_elements)
    return next(e for e in elements if e.element_id == eid)


# --------------------------------------------------------------------------- aggregation
def test_quorum_is_half_the_votes_rounded_up():
    assert [quorum(k) for k in (1, 2, 3, 4, 5)] == [1, 1, 2, 2, 3]


def test_majority_counts_failed_votes_as_unclear():
    # one real vote and two failures: no majority, every element unclear, tally adds up to k
    elements, flags = aggregate.majority([vote()], RULE, failed=2)
    assert all(e.status == "unclear" for e in elements)
    assert all(e.votes == {"included": 1, "missing": 0, "unclear": 2} for e in elements)
    assert FLAG_VOTE_DISAGREEMENT not in flags  # the model did not disagree, it did not answer
    assert elements[0].reasoning.startswith("Only 1 of 3 model assessments completed")
    # two agreeing votes and one failure: the majority stands and the failure is visible in the tally
    elements, flags = aggregate.majority([vote(), vote()], RULE, failed=1)
    assert all(e.status == "included" for e in elements) and not flags
    assert all(e.votes == {"included": 2, "missing": 0, "unclear": 1} for e in elements)
    # a 1-1 split with one failure is a disagreement, not a decision
    elements, flags = aggregate.majority([vote(), vote(missing=("refusal_date",))], RULE, failed=1)
    assert element(elements, "refusal_date").status == "unclear" and FLAG_VOTE_DISAGREEMENT in flags
    assert element(elements, "refusal_date").votes == {"included": 1, "missing": 1, "unclear": 1}
    # no votes completed at all
    elements, flags = aggregate.majority([], RULE, failed=3)
    assert all(e.status == "unclear" and e.votes == {"included": 0, "missing": 0, "unclear": 3} for e in elements) and not flags
    # without failures nothing changes: a single vote still decides on its own
    elements, flags = aggregate.majority([vote()], RULE)
    assert all(e.status == "included" for e in elements) and not flags


# --------------------------------------------------------------------------- pipeline
def test_pipeline_gives_each_vote_its_own_index_and_all_three_count():
    fake = FakeLLM([vote(), vote(), vote()])
    res = run(fake)
    assert sorted(fake.calls) == [0, 1, 2]
    assert res.verdict == "meets", [(e.element_id, e.status) for e in res.elements]
    assert res.votes == 3 and res.votes_failed == 0
    assert all(e.votes == {"included": 3, "missing": 0, "unclear": 0} for e in res.elements)


def test_two_failed_votes_out_of_three_go_to_a_caseworker_as_model_error():
    fake = FakeLLM([vote(), RuntimeError("upstream timeout"), RuntimeError("upstream timeout")])
    res = run(fake)
    assert res.verdict == "needs_caseworker"
    assert FLAG_MODEL_ERROR in res.flags and FLAG_REFUSAL not in res.flags
    assert "could not be completed reliably" in res.provider_summary and "2 of 3" in res.provider_summary
    assert res.votes == 3 and res.votes_failed == 2
    assert all(e.status == "unclear" for e in res.elements)
    assert element(res, "refusal_date").votes == {"included": 1, "missing": 0, "unclear": 2}
    assert res.request_letter is None  # nothing is known to be missing, so nothing to ask the author for
    # the applicant only ever sees the neutral wording
    assert res.client_message == "Thank you. Your solicitor will look at this document and be in touch."


def test_one_failed_vote_with_two_agreeing_keeps_the_majority():
    fake = FakeLLM([vote(), RuntimeError("boom"), vote()])
    res = run(fake)
    assert res.verdict == "meets", [(e.element_id, e.status) for e in res.elements]
    assert FLAG_MODEL_ERROR not in res.flags and FLAG_VOTE_DISAGREEMENT not in res.flags
    assert res.votes_failed == 1
    for e in res.elements:
        assert e.status == "included" and e.quote_verified
        assert e.votes == {"included": 2, "missing": 0, "unclear": 1}


def test_one_failed_vote_breaks_a_split_decision():
    # included / missing / failed: no strict majority on the split element
    res = run(FakeLLM([vote(), vote(missing=("refusal_date",)), RuntimeError("boom")]))
    assert res.verdict == "needs_caseworker"
    assert FLAG_VOTE_DISAGREEMENT in res.flags and FLAG_MODEL_ERROR not in res.flags
    assert element(res, "refusal_date").status == "unclear"
    assert element(res, "refusal_date").votes == {"included": 1, "missing": 1, "unclear": 1}


def test_a_refusal_is_a_failed_vote_unless_every_vote_refuses():
    res = run(FakeLLM([vote(), RefusalError("declined"), vote()]))
    assert res.verdict == "meets" and res.votes_failed == 1 and FLAG_REFUSAL not in res.flags
    res = run(FakeLLM([RefusalError("declined")] * 3))
    assert res.verdict == "needs_caseworker" and FLAG_REFUSAL in res.flags and res.votes_failed == 3


def test_every_vote_failing_without_a_refusal_is_a_model_error_not_a_crash():
    res = run(FakeLLM([RuntimeError("boom")] * 3))
    assert res.verdict == "needs_caseworker" and FLAG_MODEL_ERROR in res.flags
    assert res.votes_failed == 3
    assert all(e.status == "unclear" and e.votes == {"included": 0, "missing": 0, "unclear": 3} for e in res.elements)


def test_single_vote_still_decides_when_it_completes():
    res = run(FakeLLM([vote()]), votes=1)
    assert res.verdict == "meets" and res.votes == 1 and res.votes_failed == 0
    res = run(FakeLLM([RuntimeError("boom")]), votes=1)
    assert res.verdict == "needs_caseworker" and FLAG_MODEL_ERROR in res.flags and res.votes_failed == 1


# --------------------------------------------------------------------------- record / replay
def test_cached_llm_records_and_replays_three_distinct_votes(tmp_path):
    fake = FakeLLM([vote(), vote(), vote(missing=("refusal_date",))])
    recorded = run(CachedLLM(fake, tmp_path, mode="on"))
    assert sorted(fake.calls) == [0, 1, 2]
    assert element(recorded, "refusal_date").votes == {"included": 2, "missing": 1, "unclear": 0}
    assert len(list(tmp_path.glob("assess-*.json"))) == 3

    class NeverCalled(FakeLLM):
        async def assess(self, *args, **kwargs):
            raise AssertionError("replay must not call the model")

    replayed = run(CachedLLM(NeverCalled([]), tmp_path, mode="replay", fallback=None))
    assert element(replayed, "refusal_date").votes == {"included": 2, "missing": 1, "unclear": 0}
    assert replayed.verdict == recorded.verdict == "meets"
    assert [(e.element_id, e.status) for e in replayed.elements] == [(e.element_id, e.status) for e in recorded.elements]


def test_cached_llm_assess_keys_on_the_vote_index(tmp_path):
    fake = FakeLLM([vote(), vote(missing=("refusal_date",)), vote(missing=("perpetrator_named",))])
    cached = CachedLLM(fake, tmp_path, mode="on")

    async def three(llm):
        return [await llm.assess(TEXT, RULE, "Jane Doe", "John Doe", [], None, vote=i) for i in range(3)]

    first = asyncio.run(three(cached))
    assert [element(a, "refusal_date").status for a in first] == ["included", "missing", "included"]
    assert [element(a, "perpetrator_named").status for a in first] == ["included", "included", "missing"]
    assert fake.calls == [0, 1, 2]
    again = asyncio.run(three(cached))
    assert fake.calls == [0, 1, 2]  # every vote served from its own recording
    assert [a.model_dump() for a in again] == [a.model_dump() for a in first]


def test_replay_falls_back_to_a_legacy_single_recording_before_the_stub(tmp_path):
    """Recordings made before votes were indexed hold only vote 0; replay serves it for every vote rather than the offline stub."""
    legacy = FakeLLM([vote(missing=("refusal_date",))])
    asyncio.run(CachedLLM(legacy, tmp_path, mode="on").assess(TEXT, RULE, "Jane Doe", "John Doe", [], None))  # vote defaults to 0
    assert len(list(tmp_path.glob("assess-*.json"))) == 1
    replay = CachedLLM(FakeLLM([]), tmp_path, mode="replay", fallback=OfflineLLM())
    a = asyncio.run(replay.assess(TEXT, RULE, "Jane Doe", "John Doe", [], None, vote=2))
    assert element(a, "refusal_date").status == "missing" and a.elements[0].reasoning == "fake"
    # a document with no recording at all still falls back to the stub
    b = asyncio.run(replay.assess("Something else entirely.", RULE, "Jane Doe", "John Doe", [], None, vote=1))
    assert b.elements[0].reasoning.startswith("offline stub")


def test_offline_llm_accepts_the_vote_keyword():
    a = asyncio.run(OfflineLLM().assess(TEXT, RULE, "Jane Doe", "John Doe", [], None, vote=2))
    assert isinstance(a, Assessment) and len(a.elements) == len(RULE.elements)
