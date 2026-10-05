"""Quote verification: the anti-hallucination guardrail.

A requirement can only be "included" if the model quotes wording that is in the
document. We first look for the quote verbatim after normalising whitespace and
curly quotes. If that fails, a fuzzy partial match at or above the gateway
threshold is accepted but flagged so a reader can see it was not exact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def normalise(s: str) -> str:
    s = s.translate(_QUOTES)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


@dataclass
class QuoteCheck:
    verified: bool
    exact: bool
    score: float
    start: int | None = None  # offsets into the ORIGINAL text, for highlighting
    end: int | None = None


def locate(quote: str, text: str) -> tuple[int, int] | None:
    """Find the quote in the original text ignoring case, whitespace and quote style."""
    tokens = normalise(quote).split(" ")
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    # allow either quote style in the source
    pattern = pattern.replace(re.escape("'"), "[‘’']").replace(re.escape('"'), '[“”"]')
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def check_quote(quote: str | None, text: str, fuzzy_threshold: int = 90) -> QuoteCheck:
    if not quote or not quote.strip():
        return QuoteCheck(verified=False, exact=False, score=0.0)
    span = locate(quote, text)
    if span:
        return QuoteCheck(verified=True, exact=True, score=100.0, start=span[0], end=span[1])
    score = fuzz.partial_ratio(normalise(quote), normalise(text))
    if score >= fuzzy_threshold:
        return QuoteCheck(verified=True, exact=False, score=float(score))
    return QuoteCheck(verified=False, exact=False, score=float(score))
