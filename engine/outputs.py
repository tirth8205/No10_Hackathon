"""Text for each audience. Templated from the rule's fix strings so the content is
deterministic; the model never writes to the client or the letter author directly.
"""
from __future__ import annotations

from engine.models import Application, CaseResult, DocumentResult, ElementResult
from engine.rules import Rule

CLIENT_MESSAGES = {
    "meets": "Thank you. This document looks complete. Your solicitor will check it.",
    "needs_change": "This document may need a little more detail. Your solicitor will help you get it.",
    "needs_caseworker": "Thank you. Your solicitor will look at this document and be in touch.",
    "not_prescribed": "This document may not be the right kind for legal aid. Your solicitor will talk to you about other options.",
}
CLIENT_ILLEGIBLE = "We could not read this clearly. You could try another photo in good light."


def _fmt(s: str | None, application: Application, author_org: str | None) -> str:
    if not s:
        return ""
    return s.format(
        applicant_name=application.applicant_name,
        other_party_name=application.other_party_name or "the other party",
        author_org=author_org or "the organisation",
    )


def provider_summary(rule: Rule | None, elements: list[ElementResult], verdict: str) -> str:
    if rule is None:
        return "Not an accepted evidence type for the domestic abuse gateway."
    required = [e for e in elements if (rule.element(e.element_id) or rule.elements[0]).kind == "required"]
    included = [e for e in required if e.status == "included"]
    missing = [e for e in required if e.status == "missing"]
    unclear = [e for e in required if e.status == "unclear"]
    head = f"Paragraph {rule.paragraph}, {rule.short_name.lower()}: {len(included)} of {len(required)} requirements included."
    parts = []
    if missing:
        parts.append("Missing: " + "; ".join(e.label.lower() for e in missing) + ".")
    if unclear:
        parts.append("Needs a check: " + "; ".join(e.label.lower() for e in unclear) + ".")
    if verdict == "needs_caseworker" and not parts:
        parts.append("A caseworker must decide this type of evidence.")
    return " ".join([head, *parts])


CLIENT_WRONG_NAMES = ("If you uploaded the wrong letter, upload the right one. "
                      "If the names in the letter are wrong, ask the person who wrote it to correct them.")


def client_message(verdict: str, illegible: bool = False, name_check: str | None = None) -> str:
    if illegible:
        return CLIENT_ILLEGIBLE
    if name_check and verdict == "needs_change":
        return f"{name_check} {CLIENT_WRONG_NAMES}"
    return CLIENT_MESSAGES.get(verdict, CLIENT_MESSAGES["needs_caseworker"])


def request_letter(rule: Rule | None, elements: list[ElementResult], application: Application, author_name: str | None, author_org: str | None,
                   name_check: str | None = None) -> str | None:
    if rule is None:
        return None
    gaps = [e for e in elements if e.status in ("missing", "unclear")]
    if not gaps:
        return None
    to = author_name or author_org or "the author"
    lines = [
        f"Dear {to},",
        "",
        f"Re: {application.applicant_name}",
        "",
        f"Thank you for your letter in support of {application.applicant_name}'s application for legal aid. "
        + (f"{name_check} " if name_check else "")
        + f"To be accepted as evidence under {rule.legal_ref}, the letter needs to confirm the following, which the current letter does not clearly show:",
        "",
    ]
    for e in gaps:
        fix = _fmt(e.fix or (rule.element(e.element_id).fix if rule.element(e.element_id) else None), application, author_org)
        lines.append(f"- {fix}")
    lines += [
        "",
        "Exact wording is not required, but the meaning must be clear and the statements must be made without qualification "
        "(for example, 'is consistent with' rather than 'might be consistent with').",
    ]
    if rule.gov_template_url:
        lines += ["", f"A template letter is available at {rule.gov_template_url}"]
    lines += ["", "Please return the amended letter on headed paper or from an official email address.", "", "Kind regards,"]
    return "\n".join(lines)


def return_note(doc: DocumentResult, rule: Rule | None) -> str:
    if rule is None:
        return "The document submitted is not one of the forms of evidence listed in Schedule 1 to the Civil Legal Aid (Procedure) Regulations 2012."
    gaps = [e for e in doc.elements if e.status in ("missing", "unclear")]
    if not gaps:
        return f"The evidence submitted under Schedule 1, paragraph {rule.paragraph} appears to meet the requirements."
    lines = [f"The evidence submitted under Schedule 1, paragraph {rule.paragraph} ({rule.short_name.lower()}) does not meet the requirements because:"]
    for e in gaps:
        word = "does not show" if e.status == "missing" else "does not clearly show"
        lines.append(f"- it {word} that {rule.element(e.element_id).requirement[0].lower() + rule.element(e.element_id).requirement[1:] if rule.element(e.element_id) else e.label}" + (f" ({e.reasoning})" if e.reasoning else ""))
    lines.append("Please provide an amended letter addressing the points above, or alternative prescribed evidence.")
    return "\n".join(lines)


def verification_summary(case: CaseResult) -> dict:
    return {
        "case_verdict": case.verdict,
        "documents": [
            {
                "document_id": d.document_id,
                "filename": d.filename,
                "paragraph": d.paragraph,
                "rule_id": d.rule_id,
                "verdict": d.verdict,
                "flags": d.flags,
                "recategorise_to": d.recategorise_to,
                "elements": [
                    {"id": e.element_id, "label": e.label, "status": e.status, "quote": e.quote, "quote_verified": e.quote_verified, "votes": e.votes}
                    for e in d.elements
                ],
                "rules_version": d.rules_version,
                "model": d.model,
            }
            for d in case.documents
        ],
    }
