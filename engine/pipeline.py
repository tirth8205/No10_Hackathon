"""check_document() and check_case(): the one path every surface uses.

  ingest -> classify -> assess x k (parallel) -> verify quotes -> gateway checks
  -> verdict -> outputs
"""
from __future__ import annotations

import asyncio
import time

from engine import aggregate, outputs
from engine.ingest import Ingested, ingest
from engine.llm import LLM, RefusalError, get_llm
from engine.models import (
    FLAG_ILLEGIBLE,
    FLAG_REFUSAL,
    NOT_PRESCRIBED,
    Application,
    Assessment,
    CaseResult,
    Classification,
    DocumentResult,
    Parties,
)
from engine.rules import Rule, RuleSet, load_rules


def rule_for_paragraph(rules: RuleSet, paragraph: str | None) -> Rule | None:
    if not paragraph:
        return None
    p = str(paragraph).strip().upper()
    return next((r for r in rules.enabled() if r.paragraph.upper() == p), None)


async def _votes(llm: LLM, text: str, rule: Rule, application: Application, rules: RuleSet, k: int) -> list[Assessment]:
    hedges = rules.gateway.hedge_terms
    results = await asyncio.gather(
        *[llm.assess(text, rule, application.applicant_name, application.other_party_name, hedges, application.application_date) for _ in range(k)],
        return_exceptions=True,
    )
    good = [r for r in results if isinstance(r, Assessment)]
    errors = [r for r in results if isinstance(r, Exception)]
    if not good:
        raise errors[0] if errors else RuntimeError("no assessments")
    return good


def _assemble(text: str, rule: Rule, votes: list[Assessment], classification: Classification, parties: Parties,
              application: Application, rules: RuleSet) -> tuple[list, list[str], str]:
    elements, flags = aggregate.majority(votes, rule)
    flags += aggregate.verify_quotes(elements, text, rules.gateway)
    party_flags, severity = aggregate.party_checks(parties, application, rule, rules.gateway, elements)
    flags += party_flags
    flags += aggregate.hedge_flag(votes) + aggregate.injection_flag(votes) + aggregate.language_flag(classification) + aggregate.confidence_flag(classification)
    for f in aggregate.text_checks(text, rules.gateway):
        if f not in flags:
            flags.append(f)
    verdict = aggregate.decide(elements, classification, rule, flags, severity)
    return elements, list(dict.fromkeys(flags)), verdict


async def check_text(text: str, filename: str, application: Application, *, rules: RuleSet | None = None,
                     llm: LLM | None = None, votes: int | None = None, claimed_para: str | None = None,
                     document_id: str = "D1", ingested: Ingested | None = None) -> DocumentResult:
    from engine.config import settings

    rules = rules or load_rules()
    llm = llm or get_llm()
    k = votes or settings.votes
    t0 = time.perf_counter()
    base = dict(document_id=document_id, filename=filename, rules_version=rules.gateway.rules_version, model=llm.name, votes=k)

    def finish(**kw) -> DocumentResult:
        kw.setdefault("classification", Classification(rule_id=NOT_PRESCRIBED, confidence="low", document_kind="other", language="en", rationale=""))
        kw.setdefault("parties", Parties())
        kw["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return DocumentResult(**base, **kw)

    if ingested is not None and ingested.needs_transcription and not text.strip():
        return finish(verdict="needs_caseworker", flags=[FLAG_ILLEGIBLE],
                      provider_summary="The document could not be read. Ask for a clearer copy.",
                      client_message=outputs.client_message("needs_caseworker", illegible=True))

    try:
        cls = await llm.classify(text, rules)
    except RefusalError as e:
        return finish(verdict="needs_caseworker", flags=[FLAG_REFUSAL], provider_summary=f"The model declined to assess this document ({e}). A caseworker must review it.",
                      client_message=outputs.client_message("needs_caseworker"))
    classification, parties = cls.classification, cls.parties

    claimed = rule_for_paragraph(rules, claimed_para)
    suggested = rules.get(classification.rule_id) if classification.rule_id != NOT_PRESCRIBED else None
    rule = claimed or suggested
    if rule is None:
        return finish(verdict="not_prescribed", classification=classification, parties=parties,
                      claimed_rule_id=None, provider_summary=outputs.provider_summary(None, [], "not_prescribed"),
                      client_message=outputs.client_message("not_prescribed"))

    try:
        votes_ = await _votes(llm, text, rule, application, rules, k)
    except RefusalError as e:
        return finish(verdict="needs_caseworker", flags=[FLAG_REFUSAL], classification=classification, parties=parties,
                      rule_id=rule.id, paragraph=rule.paragraph, rule_name=rule.name, legal_ref=rule.legal_ref,
                      provider_summary=f"The model declined to assess this document ({e}). A caseworker must review it.",
                      client_message=outputs.client_message("needs_caseworker"))
    elements, flags, verdict = _assemble(text, rule, votes_, classification, parties, application, rules)

    # If the provider claimed a paragraph the document does not meet, see whether the
    # classifier's suggestion does better and offer the switch.
    recategorise_to = None
    if claimed and suggested and suggested.id != claimed.id and verdict != "meets":
        try:
            alt_votes = await _votes(llm, text, suggested, application, rules, k)
            _, _, alt_verdict = _assemble(text, suggested, alt_votes, classification, parties, application, rules)
            if alt_verdict == "meets":
                recategorise_to = suggested.id
        except RefusalError:
            pass

    return finish(
        verdict=verdict, flags=flags, elements=elements, classification=classification, parties=parties,
        rule_id=rule.id, paragraph=rule.paragraph, rule_name=rule.name, legal_ref=rule.legal_ref,
        claimed_rule_id=claimed.id if claimed else None, recategorise_to=recategorise_to,
        provider_summary=outputs.provider_summary(rule, elements, verdict) + (
            f" This letter appears to meet paragraph {suggested.paragraph} ({suggested.short_name.lower()}) instead." if recategorise_to else ""),
        client_message=outputs.client_message(verdict),
        request_letter=outputs.request_letter(rule, elements, application, classification.author_name, classification.author_org) if verdict in ("needs_change", "needs_caseworker") else None,
    )


async def check_document(data: bytes, filename: str, application: Application, **kw) -> DocumentResult:
    ing = ingest(data, filename)
    text = ing.text
    if ing.needs_transcription:
        llm = kw.get("llm") or get_llm()
        kw["llm"] = llm
        try:
            tr = await llm.transcribe(ing.data, ing.media_type)
            text = tr.text if tr.legible or tr.text.strip() else text
        except RefusalError:
            pass
    return await check_text(text, filename, application, ingested=ing, **kw)


async def check_case(case_id: str, docs: list[tuple[str, str, str | None]], application: Application, **kw) -> CaseResult:
    """docs: list of (document_id, text, claimed_para)."""
    results = await asyncio.gather(*[check_text(t, f"{d}.txt", application, document_id=d, claimed_para=p, **kw) for d, t, p in docs])
    case = CaseResult(case_id=case_id, verdict=aggregate.case_verdict(list(results)), documents=list(results))
    case.verification_summary = outputs.verification_summary(case)
    return case
