"""Quote verification: the anti-hallucination guardrail.

A requirement can only be "included" if the model quotes wording that is in the
document. We first look for the quote verbatim after normalising whitespace,
quotes and dashes. A quote made of several passages (the model sometimes joins
the letterhead and the sign-off, or two sentences with one dropped between) is
accepted only if every fragment is found verbatim, in order; it is flagged as
multi-span. Only if that fails do we fall back to a fuzzy partial match at or
above the gateway threshold, which is flagged so a reader can see it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " ", "…": "..."})
_FRAGMENT_SPLIT = re.compile(r"\s*\.\.\.\s*|\n+|(?<=[.!?])\s+(?=[A-Z(\[\d])")  # never on ":" (header lines) or ";"
MIN_FRAGMENT_TOKENS = 3


def normalise(s: str) -> str:
    s = s.translate(_QUOTES)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


@dataclass
class QuoteCheck:
    verified: bool
    exact: bool
    score: float
    multi: bool = False
    spans: list[tuple[int, int]] = field(default_factory=list)  # offsets into the ORIGINAL text, for highlighting

    @property
    def start(self) -> int | None:
        return self.spans[0][0] if self.spans else None

    @property
    def end(self) -> int | None:
        return self.spans[-1][1] if self.spans else None


def _pattern(quote: str) -> str | None:
    tokens = normalise(quote).split(" ")
    if not tokens or tokens == [""]:
        return None
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    # allow either quote and dash style in the source
    return (pattern.replace(re.escape("'"), "[‘’']").replace(re.escape('"'), '[“”"]')
            .replace(re.escape("-"), "[-–—]").replace(re.escape("..."), "(?:\\.\\.\\.|…)"))


def locate(quote: str, text: str, start: int = 0) -> tuple[int, int] | None:
    """Find the quote in the original text ignoring case, whitespace, quote and dash style."""
    pattern = _pattern(quote)
    if pattern is None:
        return None
    m = re.compile(pattern, re.IGNORECASE).search(text, start)
    return (m.start(), m.end()) if m else None


def spans(quote: str, text: str) -> list[tuple[int, int]]:
    """Offsets of the quote in the text: one span if contiguous, else one per verbatim fragment (in order), else []."""
    whole = locate(quote, text)
    if whole:
        return [whole]
    fragments = [f for f in _FRAGMENT_SPLIT.split(quote.translate(_QUOTES)) if f and len(f.split()) >= MIN_FRAGMENT_TOKENS]
    if len(fragments) < 2:
        return []
    out, pos = [], 0
    for f in fragments:
        span = locate(f, text, pos) or locate(f, text)  # prefer in-order, tolerate the model reordering
        if not span:
            return []
        out.append(span)
        pos = span[1]
    return sorted(out)


def check_quote(quote: str | None, text: str, fuzzy_threshold: int = 90) -> QuoteCheck:
    if not quote or not quote.strip():
        return QuoteCheck(verified=False, exact=False, score=0.0)
    found = spans(quote, text)
    if len(found) == 1:
        return QuoteCheck(verified=True, exact=True, score=100.0, spans=found)
    if len(found) > 1:
        return QuoteCheck(verified=True, exact=True, score=100.0, multi=True, spans=found)
    norm_text = normalise(text)
    score = fuzz.partial_ratio(normalise(quote), norm_text)
    if score >= fuzzy_threshold:
        return QuoteCheck(verified=True, exact=False, score=float(score))
    # a stitched quote where each passage is a close (not exact) match
    fragments = [f for f in _FRAGMENT_SPLIT.split(quote.translate(_QUOTES)) if f and len(f.split()) >= MIN_FRAGMENT_TOKENS]
    if len(fragments) >= 2:
        scores = [fuzz.partial_ratio(normalise(f), norm_text) for f in fragments]
        if min(scores) >= fuzzy_threshold:
            return QuoteCheck(verified=True, exact=False, score=float(min(scores)), multi=True)
    return QuoteCheck(verified=False, exact=False, score=float(score))
