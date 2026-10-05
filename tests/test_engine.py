import asyncio
import json
from pathlib import Path

import pytest

from engine import aggregate
from engine.llm import OfflineLLM
from engine.models import Application, Assessment, Classification, ElementAssessment
from engine.pipeline import check_text, rule_for_paragraph
from engine.rules import load_rules
from engine.verify import check_quote, locate

ROOT = Path(__file__).resolve().parent.parent
RULES = load_rules()
GOLD = {c["id"]: c for c in json.load(open(ROOT / "data" / "moj_gold_cases.json"))["cases"]}
SYN = {c["id"]: c for c in json.load(open(ROOT / "data" / "synthetic_cases.json"))["cases"]}


def test_rules_cover_every_paragraph_in_the_test_data():
    paras = {d["claimed_para"] for c in list(GOLD.values()) + list(SYN.values()) for d in c["documents"]}
    for p in paras:
        rule = rule_for_paragraph(RULES, p)
        assert rule is not None, p
    assert len(RULES.rules) == 22


def test_rule_elements_match_test_data_keys():
    for case in list(GOLD.values()) + list(SYN.values()):
        for d in case["documents"]:
            rule = rule_for_paragraph(RULES, d["claimed_para"])
            assert set(d["expected"]["elements"]) == {e.id for e in rule.elements}, case["id"]


def test_quote_verification_exact_fuzzy_and_missing():
    text = "I can confirm that Jane Doe sought admission to a refuge because of allegations of domestic abuse by John Doe."
    assert check_quote("sought admission to a refuge", text).exact
    # whitespace and curly quotes are normalised
    assert check_quote("sought  admission\nto a refuge", text).exact
    fuzzy = check_quote("sought admission to the refuge because of allegations", text)
    assert fuzzy.verified and not fuzzy.exact
    assert not check_quote("the applicant was examined in person", text).verified
    assert locate("Jane Doe", text) == (19, 27)


def test_name_matching_levels():
    t = RULES.gateway.name_match_threshold
    assert aggregate.name_match("Ms Jane Doe", "Jane Doe", t) == "exact"
    assert aggregate.name_match("Ms Doe", "Jane Doe", t) == "exact"
    assert aggregate.name_match("Amira Hussain", "Amira Hussaun", t) == "near"
    assert aggregate.name_match("Arjun Begum", "Rhys Patel", t) == "far"
    assert aggregate.name_match(None, "Jane Doe", t) == "unknown"


def _vote(statuses: dict[str, str], quote="q"):
    return Assessment(elements=[ElementAssessment(element_id=k, status=v, quote=quote if v == "included" else None, reasoning="r") for k, v in statuses.items()],
                      hedging_detected=False, injection_detected=False)


def test_majority_vote_and_disagreement():
    rule = RULES.get("sch1_p14_idva")
    ids = [e.id for e in rule.elements]
    votes = [_vote(dict.fromkeys(ids, "included")), _vote(dict.fromkeys(ids, "included")), _vote({**dict.fromkeys(ids, "included"), "confirms_support": "missing"})]
    elements, flags = aggregate.majority(votes, rule)
    assert all(e.status == "included" for e in elements) and not flags
    split = [_vote({**dict.fromkeys(ids, "included"), "confirms_support": "missing"}), _vote(dict.fromkeys(ids, "included"))]
    elements, flags = aggregate.majority(split, rule)
    assert next(e for e in elements if e.element_id == "confirms_support").status == "unclear"
    assert "vote_disagreement" in flags


def test_decision_table():
    rule = RULES.get("sch1_p18_refuge_refusal")
    cls = Classification(rule_id=rule.id, confidence="high", document_kind="letter", language="en", rationale="")
    els, _ = aggregate.majority([_vote(dict.fromkeys([e.id for e in rule.elements], "included"))], rule)
    assert aggregate.decide(els, cls, rule, [], "none") == "meets"
    els[1].status = "missing"
    assert aggregate.decide(els, cls, rule, [], "none") == "needs_change"
    els[1].status = "unclear"
    assert aggregate.decide(els, cls, rule, [], "none") == "needs_caseworker"
    assert aggregate.decide(els, cls, rule, ["injection"], "none") == "needs_caseworker"
    p21 = RULES.get("sch1_p21_economic_abuse")
    els21, _ = aggregate.majority([_vote(dict.fromkeys([e.id for e in p21.elements], "included"))], p21)
    assert aggregate.decide(els21, cls, p21, [], "none") == "needs_caseworker"


def test_case_verdict_prefers_meets_then_caseworker():
    from engine.models import DocumentResult, Parties

    def doc(v):
        return DocumentResult(document_id="d", filename="f", classification=Classification(rule_id="x", confidence="high", document_kind="letter", language="en", rationale=""),
                              parties=Parties(), verdict=v)
    assert aggregate.case_verdict([doc("needs_change"), doc("meets")]) == "meets"
    assert aggregate.case_verdict([doc("needs_change"), doc("needs_caseworker")]) == "needs_caseworker"
    assert aggregate.case_verdict([doc("needs_change")]) == "needs_change"
    assert aggregate.case_verdict([]) == "no_evidence_yet"


def _run(case_id, source=GOLD, votes=1):
    case = source[case_id]
    d = case["documents"][0]
    app = Application(applicant_name=case["application"]["applicant"], other_party_name=case["application"].get("other_party"))
    return asyncio.run(check_text(d["text"], "t.txt", app, rules=RULES, llm=OfflineLLM(), votes=votes, claimed_para=d["claimed_para"]))


def test_offline_pipeline_refuge_letter_without_perpetrator_needs_change():
    res = _run("MOJ-P18-rejected-02")
    assert res.verdict == "needs_change"
    assert next(e for e in res.elements if e.element_id == "perpetrator_named").status == "missing"
    assert all(e.quote_verified for e in res.elements if e.status == "included")
    assert res.request_letter and "paragraph 18" in res.request_letter
    assert "rejected" not in res.client_message.lower() and "fail" not in res.client_message.lower()


def test_offline_pipeline_accepted_refuge_letter_meets():
    res = _run("MOJ-P18-accepted-01")
    assert res.verdict == "meets", [(e.element_id, e.status) for e in res.elements]
    assert res.request_letter is None


def test_offline_pipeline_hedged_health_letter_fails_on_judgement():
    res = _run("MOJ-P11-rejected-02")
    assert next(e for e in res.elements if e.element_id == "consistent_with_domestic_abuse").status == "missing"
    assert "hedge" in res.flags


def test_name_mismatch_routes_to_caseworker():
    res = _run("X-name_mismatch", source=SYN)
    assert res.verdict == "needs_caseworker"
    assert "victim_name_mismatch" in res.flags
    assert next(e for e in res.elements if e.element_id == "applicant_named").status == "unclear"


def test_economic_abuse_always_goes_to_a_person():
    res = _run("P21-valid-01", source=SYN)
    assert res.verdict == "needs_caseworker"


def test_rules_version_recorded():
    res = _run("MOJ-P14-accepted-01")
    assert res.rules_version == RULES.gateway.rules_version
    assert res.paragraph == "14"
