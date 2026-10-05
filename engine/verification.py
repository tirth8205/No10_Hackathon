"""Verification checks on the author and organisation of a document (stub; see tests/test_verification.py).

verify_document() returns a list of VerificationCheck. It must never raise and must
finish within a few seconds: network lookups use short timeouts and degrade to
status "unknown".
"""
from __future__ import annotations

from engine.models import Classification, Parties, VerificationCheck
from engine.rules import Rule


async def verify_document(text: str, classification: Classification, parties: Parties, rule: Rule | None, *, timeout: float = 4.0) -> list[VerificationCheck]:
    return []
