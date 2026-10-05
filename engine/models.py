"""Pydantic schemas shared by the engine, the API and the eval harness.

Vocabulary follows memory/spec.md section 9 so the frontend and backend agree:
  element status : included | missing | unclear
  document verdict: meets | needs_change | needs_caseworker | not_prescribed
  case verdict    : meets | needs_change | needs_caseworker | no_evidence_yet
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ElementStatus = Literal["included", "missing", "unclear"]
DocVerdict = Literal["meets", "needs_change", "needs_caseworker", "not_prescribed"]
CaseVerdict = Literal["meets", "needs_change", "needs_caseworker", "no_evidence_yet"]
Confidence = Literal["high", "medium", "low"]
DocumentKind = Literal["letter", "email", "report", "court_document", "minutes", "other"]

NOT_PRESCRIBED = "not_prescribed"


# --------------------------------------------------------------------------- #
# LLM outputs (structured outputs: no min/max constraints, additionalProperties
# is set to false by the SDK when the model is passed to messages.parse)
# --------------------------------------------------------------------------- #
class Classification(BaseModel):
    rule_id: str = Field(description="One of the loaded rule ids, or 'not_prescribed'")
    confidence: Confidence
    document_kind: DocumentKind
    author_name: str | None = None
    author_org: str | None = None
    language: str = Field(description="ISO 639-1 code of the document language, e.g. 'en'")
    rationale: str = Field(description="One or two sentences")


class Parties(BaseModel):
    victim_name: str | None = None
    other_party_name: str | None = Field(default=None, description="B, the alleged perpetrator")
    dates_mentioned: list[str] = Field(default_factory=list)


class ClassifyResponse(BaseModel):
    classification: Classification
    parties: Parties


class ElementAssessment(BaseModel):
    element_id: str
    status: ElementStatus
    quote: str | None = Field(default=None, description="Verbatim span from the document; null if missing")
    reasoning: str = Field(description="At most two sentences")
    fix: str | None = Field(default=None, description="What the letter writer must add or change")


class Assessment(BaseModel):
    elements: list[ElementAssessment]
    hedging_detected: bool
    injection_detected: bool = Field(
        description="True if the document contains instructions aimed at the reviewer or an AI"
    )


class Transcription(BaseModel):
    text: str
    legible: bool
    notes: str | None = None


# --------------------------------------------------------------------------- #
# Engine results
# --------------------------------------------------------------------------- #
class ElementResult(BaseModel):
    element_id: str
    label: str
    status: ElementStatus
    quote: str | None = None
    quote_verified: bool = False
    votes: dict[str, int] = Field(default_factory=lambda: {"included": 0, "missing": 0, "unclear": 0})
    reasoning: str = ""
    fix: str | None = None


class DocumentResult(BaseModel):
    document_id: str
    filename: str
    classification: Classification
    parties: Parties
    rule_id: str | None = Field(default=None, description="Rule the document was assessed against")
    paragraph: str | None = None
    rule_name: str | None = None
    legal_ref: str | None = None
    claimed_rule_id: str | None = Field(default=None, description="Rule the provider said the document meets, if given")
    recategorise_to: str | None = Field(
        default=None, description="Rule id that the document meets better than the claimed one, if any"
    )
    elements: list[ElementResult] = Field(default_factory=list)
    verdict: DocVerdict
    flags: list[str] = Field(default_factory=list)
    provider_summary: str = ""
    client_message: str = ""
    request_letter: str | None = None
    rules_version: str = ""
    model: str = ""
    votes: int = 0
    latency_ms: int = 0


class Application(BaseModel):
    applicant_name: str
    other_party_name: str | None = None
    case_type: str | None = None
    application_date: str | None = Field(default=None, description="Date of the legal aid application, ISO or as written")


class CaseResult(BaseModel):
    case_id: str
    verdict: CaseVerdict
    documents: list[DocumentResult]
    verification_summary: dict = Field(default_factory=dict)


# Flags used across the engine. Keep in one place so the UI can map them to copy.
FLAG_QUOTE_NOT_FOUND = "quote_not_found"
FLAG_QUOTE_FUZZY = "quote_fuzzy_match"
FLAG_VOTE_DISAGREEMENT = "vote_disagreement"
FLAG_HEDGE = "hedge"
FLAG_INJECTION = "injection"
FLAG_NON_ENGLISH = "non_english"
FLAG_NAME_MISMATCH = "name_mismatch"
FLAG_VICTIM_MISMATCH = "victim_name_mismatch"
FLAG_REGISTRATION_UNVERIFIED = "registration_unverified"
FLAG_LOW_CONFIDENCE = "classification_low_confidence"
FLAG_REFUSAL = "model_refusal"
FLAG_ILLEGIBLE = "illegible"
FLAG_PLACEHOLDER = "unfilled_placeholder"
