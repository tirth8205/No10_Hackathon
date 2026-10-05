"""Turn k model votes into one checked result, then apply the gateway rules that
live in code rather than in the model: majority voting, quote verification,
party name checks, language, hedging, injection and the verdict decision table.
"""
from __future__ import annotations

import re
from collections import Counter

from rapidfuzz import fuzz

from engine.models import (
    FLAG_HEDGE,
    FLAG_INJECTION,
    FLAG_LOW_CONFIDENCE,
    FLAG_NAME_MISMATCH,
    FLAG_NON_ENGLISH,
    FLAG_PLACEHOLDER,
    FLAG_QUOTE_FUZZY,
    FLAG_QUOTE_MULTI,
    FLAG_QUOTE_NOT_FOUND,
    FLAG_VICTIM_MISMATCH,
    FLAG_VOTE_DISAGREEMENT,
    Application,
    Assessment,
    Classification,
    DocumentResult,
    ElementResult,
    Parties,
)
from engine.rules import Gateway, Rule
from engine.verify import check_quote

_TITLES = re.compile(r"\b(ms|mr|mrs|miss|dr|mx|master)\.?\s+", re.I)


def normalise_name(name: str | None) -> str:
    if not name:
        return ""
    s = _TITLES.sub("", name.lower())
    s = re.sub(r"[^a-z\s'-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def name_match(a: str | None, b: str | None, threshold: int) -> str:
    """exact | near | far | unknown"""
    na, nb = normalise_name(a), normalise_name(b)
    if not na or not nb:
        return "unknown"
    if na == nb or na in nb or nb in na:
        return "exact"
    score = fuzz.token_sort_ratio(na, nb)
    if score >= threshold:
        return "near"
    # surname-only match (e.g. "Ms Doe" vs "Jane Doe") counts as exact enough
    if na.split()[-1] == nb.split()[-1] and (len(na.split()) == 1 or len(nb.split()) == 1):
        return "exact"
    return "far"


def majority(votes: list[Assessment], rule: Rule) -> tuple[list[ElementResult], list[str]]:
    flags: list[str] = []
    results: list[ElementResult] = []
    n = len(votes)
    for el in rule.elements:
        per_vote = [next((e for e in v.elements if e.element_id == el.id), None) for v in votes]
        per_vote = [e for e in per_vote if e is not None]
        counts = Counter(e.status for e in per_vote)
        tally = {"included": counts.get("included", 0), "missing": counts.get("missing", 0), "unclear": counts.get("unclear", 0)}
        if not per_vote:
            status = "unclear"
        else:
            status, top = counts.most_common(1)[0]
            if top * 2 <= n and n > 1:  # no strict majority
                status = "unclear"
                if FLAG_VOTE_DISAGREEMENT not in flags:
                    flags.append(FLAG_VOTE_DISAGREEMENT)
        agreeing = [e for e in per_vote if e.status == status] or per_vote
        quote = next((e.quote for e in agreeing if e.quote), None) if status == "included" else None
        reasoning = next((e.reasoning for e in agreeing if e.reasoning), "")
        fix = None if status == "included" else next((e.fix for e in agreeing if e.fix), None) or el.fix
        results.append(ElementResult(element_id=el.id, label=el.label, status=status, quote=quote, votes=tally, reasoning=reasoning, fix=fix,
                                     client_hint=None if status == "included" else el.client_hint))
    return results, flags


def verify_quotes(elements: list[ElementResult], text: str, gateway: Gateway) -> list[str]:
    flags: list[str] = []
    for el in elements:
        if el.status != "included":
            continue
        check = check_quote(el.quote, text, gateway.quote_fuzzy_threshold)
        el.quote_verified = check.verified
        if not check.verified:
            el.status = "unclear"
            el.reasoning = (el.reasoning + " " if el.reasoning else "") + "The quoted wording could not be found in the document, so this needs a person to check."
            if FLAG_QUOTE_NOT_FOUND not in flags:
                flags.append(FLAG_QUOTE_NOT_FOUND)
        elif not check.exact and FLAG_QUOTE_FUZZY not in flags:
            flags.append(FLAG_QUOTE_FUZZY)
        elif check.multi and FLAG_QUOTE_MULTI not in flags:
            flags.append(FLAG_QUOTE_MULTI)
    return flags


def party_checks(parties: Parties, application: Application, rule: Rule, gateway: Gateway, elements: list[ElementResult]) -> tuple[list[str], str]:
    """Returns (flags, severity) where severity is none | caseworker | change."""
    flags: list[str] = []
    severity = "none"
    victim = name_match(parties.victim_name, application.applicant_name, gateway.name_match_threshold)
    if rule.applicant_must_be_victim and victim in ("near", "far"):
        flags.append(FLAG_VICTIM_MISMATCH)
        # a typo needs a human; a different person is a real gap (the letter is about someone else)
        severity = "caseworker" if victim == "near" else "change"
        for el in elements:
            if el.element_id in ("applicant_named", "victim_named") and el.status == "included":
                el.status = "unclear" if victim == "near" else "missing"
                el.quote_verified = False
                el.reasoning = f"The document names '{parties.victim_name}' but the application is for '{application.applicant_name}'."
                el.fix = f"Confirm the letter is about {application.applicant_name} and correct the name."
    if rule.names_other_party_required and application.other_party_name:
        other = name_match(parties.other_party_name, application.other_party_name, gateway.name_match_threshold)
        if other in ("near", "far"):
            flags.append(FLAG_NAME_MISMATCH)
            severity = "change" if other == "far" else ("caseworker" if severity == "none" else severity)
            for el in elements:
                if ("perpetrator" in el.element_id or "other_party" in el.element_id or "respondent" in el.element_id) and el.status == "included":
                    el.status = "unclear" if other == "near" else "missing"
                    el.quote_verified = False
                    el.reasoning = f"The document names '{parties.other_party_name}' but the other party on the application is '{application.other_party_name}'."
                    el.fix = f"Confirm the letter refers to {application.other_party_name}."
    return flags, severity


def text_checks(text: str, gateway: Gateway) -> list[str]:
    flags = []
    low = text.lower()
    if any(m in low for m in gateway.injection_markers):
        flags.append(FLAG_INJECTION)
    if any(re.search(p, text, flags=re.I) for p in gateway.placeholder_patterns):
        flags.append(FLAG_PLACEHOLDER)
    return flags


def decide(elements: list[ElementResult], classification: Classification, rule: Rule, flags: list[str], party_severity: str) -> str:
    """Document verdict decision table. Order matters."""
    if FLAG_INJECTION in flags or FLAG_NON_ENGLISH in flags:
        return "needs_caseworker"
    required = [e for e in elements if rule.element(e.element_id) and rule.element(e.element_id).kind == "required"]
    missing = [e for e in required if e.status == "missing"]
    unclear = [e for e in required if e.status == "unclear"]
    if rule.always_needs_caseworker:
        return "needs_caseworker"
    if missing or party_severity == "change":
        return "needs_change"
    if unclear or party_severity == "caseworker" or FLAG_QUOTE_NOT_FOUND in flags or classification.confidence == "low":
        return "needs_caseworker"
    return "meets"


def case_verdict(documents: list[DocumentResult]) -> str:
    verdicts = {d.verdict for d in documents}
    if "meets" in verdicts:
        return "meets"
    if "needs_caseworker" in verdicts:
        return "needs_caseworker"
    if "needs_change" in verdicts:
        return "needs_change"
    return "no_evidence_yet"


def hedge_flag(votes: list[Assessment]) -> list[str]:
    return [FLAG_HEDGE] if any(v.hedging_detected for v in votes) else []


def injection_flag(votes: list[Assessment]) -> list[str]:
    n = sum(1 for v in votes if v.injection_detected)
    return [FLAG_INJECTION] if n * 2 > len(votes) else []


def language_flag(classification: Classification) -> list[str]:
    return [FLAG_NON_ENGLISH] if classification.language and classification.language.lower()[:2] not in ("en", "cy") else []


def confidence_flag(classification: Classification) -> list[str]:
    return [FLAG_LOW_CONFIDENCE] if classification.confidence == "low" else []
