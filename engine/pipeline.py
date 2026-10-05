"""check_document() and check_case(): the one path every surface uses.

  ingest -> classify -> assess x k (parallel) -> verify quotes -> gateway checks
  -> verdict -> outputs
"""
from __future__ import annotations

import asyncio
import math
import time

from engine import aggregate, outputs
from engine.ingest import Ingested, ingest
from engine.llm import LLM, RefusalError, get_llm
from engine.models import (
    FLAG_ILLEGIBLE,
    FLAG_MODEL_ERROR,
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
from engine.verification import verify_document


def rule_for_paragraph(rules: RuleSet, paragraph: str | None) -> Rule | None:
    if not paragraph:
        return None
    p = str(paragraph).strip().upper()
    return next((r for r in rules.enabled() if r.paragraph.upper() == p), None)


def quorum(k: int) -> int:
    """Votes that must complete before a check can be trusted: half of k, rounded up."""
    return math.ceil(k / 2)


async def _votes(llm: LLM, text: str, rule: Rule, application: Application, rules: RuleSet, k: int) -> tuple[list[Assessment], int]:
    """Run k independent assessments in parallel. Returns (completed votes, number that failed).

    A failed vote is never dropped: the count goes to aggregation, where it counts as "unclear"
    for every element, so one surviving vote out of three cannot decide for the other two.
    Each call carries its vote index so a record/replay cache keeps the votes apart.
    Only when every vote failed and the model refused is a RefusalError raised; the caller
    turns that into the model_refusal route.
    """
    hedges = rules.gateway.hedge_terms
    results = await asyncio.gather(
        *[llm.assess(text, rule, application.applicant_name, application.other_party_name, hedges, application.application_date, vote=i) for i in range(k)],
        return_exceptions=True,
    )
    good = [r for r in results if isinstance(r, Assessment)]
    failed = len(results) - len(good)
    if not good:
        refusal = next((r for r in results if isinstance(r, RefusalError)), None)
        if refusal is not None:
            raise refusal
    return good, failed


def _assemble(text: str, rule: Rule, votes: list[Assessment], classification: Classification, parties: Parties,
              application: Application, rules: RuleSet, failed: int = 0) -> tuple[list, list[str], str, str | None]:
    elements, flags = aggregate.majority(votes, rule, failed=failed)
    flags += aggregate.verify_quotes(elements, text, rules.gateway)
    party_flags, severity, name_check = aggregate.party_checks(parties, application, rule, rules.gateway, elements)
    flags += party_flags
    flags += aggregate.hedge_flag(votes) + aggregate.injection_flag(votes) + aggregate.language_flag(classification) + aggregate.confidence_flag(classification)
    for f in aggregate.text_checks(text, rules.gateway):
        if f not in flags:
            flags.append(f)
    verdict = aggregate.decide(elements, classification, rule, flags, severity)
    return elements, list(dict.fromkeys(flags)), verdict, name_check


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

    if not text.strip() and (ingested is None or ingested.needs_transcription or ingested.kind in ("image", "pdf", "scan")):
        return finish(verdict="needs_caseworker", flags=[FLAG_ILLEGIBLE],
                      provider_summary="The document could not be read. Ask for a clearer copy.",
                      client_message=outputs.client_message("needs_caseworker", illegible=True))

    if not text.strip():
        return finish(verdict="needs_caseworker", flags=[FLAG_ILLEGIBLE],
                      provider_summary="The document contains no readable text. Ask for a clearer copy.",
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
        good, failed = await _votes(llm, text, rule, application, rules, k)
    except RefusalError as e:
        return finish(verdict="needs_caseworker", flags=[FLAG_REFUSAL], classification=classification, parties=parties,
                      rule_id=rule.id, paragraph=rule.paragraph, rule_name=rule.name, legal_ref=rule.legal_ref, votes_failed=k,
                      provider_summary=f"The model declined to assess this document ({e}). A caseworker must review it.",
                      client_message=outputs.client_message("needs_caseworker"))
    elements, flags, verdict, name_check = _assemble(text, rule, good, classification, parties, application, rules, failed=failed)

    # Fewer than half the votes completed: whatever the survivors said, the check is not
    # reliable enough to act on. A person decides, and the summary says why.
    unreliable = len(good) < quorum(k)
    if unreliable:
        verdict = "needs_caseworker"
        flags = [FLAG_MODEL_ERROR, *flags]

    # If the provider claimed a paragraph the document does not meet, see whether the
    # classifier's suggestion does better and offer the switch.
    recategorise_to = None
    if not unreliable and claimed and suggested and suggested.id != claimed.id and verdict != "meets":
        try:
            alt_good, alt_failed = await _votes(llm, text, suggested, application, rules, k)
            if len(alt_good) >= quorum(k):
                _, _, alt_verdict, _ = _assemble(text, suggested, alt_good, classification, parties, application, rules, failed=alt_failed)
                if alt_verdict == "meets":
                    recategorise_to = suggested.id
        except RefusalError:
            pass

    try:
        verification = await asyncio.wait_for(verify_document(text, classification, parties, rule), timeout=8)
    except Exception:  # checks help a person; they never block the result
        verification = []

    if unreliable:
        summary = (f"The check could not be completed reliably: {failed} of {k} model assessments failed. "
                   "A caseworker must review this document.")
    else:
        summary = outputs.provider_summary(rule, elements, verdict) + (
            f" This letter appears to meet paragraph {suggested.paragraph} ({suggested.short_name.lower()}) instead." if recategorise_to else "")
    return finish(
        verdict=verdict, flags=flags, elements=elements, classification=classification, parties=parties, verification=verification,
        rule_id=rule.id, paragraph=rule.paragraph, rule_name=rule.name, legal_ref=rule.legal_ref, votes_failed=failed,
        claimed_rule_id=claimed.id if claimed else None, recategorise_to=recategorise_to,
        provider_summary=summary, name_check=name_check,
        client_message=outputs.client_message(verdict, name_check=name_check),
        request_letter=outputs.request_letter(rule, elements, application, classification.author_name, classification.author_org, name_check=name_check)
        if verdict in ("needs_change", "needs_caseworker") and not unreliable else None,
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
