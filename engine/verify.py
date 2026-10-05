"""Quote verification: the anti-hallucination guardrail.

A requirement can only be "included" if the model quotes wording that is in the
document. We first look for the quote verbatim after normalising whitespace,
quotes and dashes. A quote made of several passages (the model sometimes joins
the letterhead and the sign-off, or two sentences with one dropped between) is
accepted only if EVERY fragment is found verbatim, in order; it is flagged as
multi-span. Short fragments are never skipped: a two-word passage the model
invented ("Abuse confirmed.") must fail the whole quote, otherwise the guardrail
lets fabricated wording through on the back of a genuine passage. Only if that
fails do we fall back to a fuzzy partial match at or above the gateway
threshold, which is flagged so a reader can see it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " ", "…": "..."})
_FRAGMENT_SPLIT = re.compile(r"\s*\.\.\.\s*|\n+|(?<=[.!?])\s+(?=[A-Z(\[\d])")  # never on ":" (header lines) or ";"


def normalise(s: str) -> str:
    s = s.translate(_QUOTES)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def fragments(quote: str) -> list[str]:
    """Split a quote into its passages. Every fragment with at least one word is kept; only empty strings are dropped."""
    return [f.strip() for f in _FRAGMENT_SPLIT.split(quote.translate(_QUOTES)) if f and f.split()]


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
    parts = fragments(quote)
    if len(parts) < 2:
        return []
    out, pos = [], 0
    for f in parts:  # all of them, however short: one invented fragment fails the quote
        span = locate(f, text, pos) or locate(f, text)  # prefer in-order, tolerate the model reordering
        if not span:
            return []
        out.append(span)
        pos = span[1]
    return sorted(out)


def _partial(norm_quote: str, norm_text: str) -> float:
    """Fuzzy score of a quote against the text. partial_ratio aligns the SHORTER string inside the
    longer one, so a quote longer than the document would be scored by how much of the document
    it contains (100 for a document that is a prefix of the quote); compare whole-to-whole instead."""
    if len(norm_quote) > len(norm_text):
        return float(fuzz.ratio(norm_quote, norm_text))
    return float(fuzz.partial_ratio(norm_quote, norm_text))


def check_quote(quote: str | None, text: str, fuzzy_threshold: int = 90) -> QuoteCheck:
    if not quote or not quote.strip():
        return QuoteCheck(verified=False, exact=False, score=0.0)
    found = spans(quote, text)
    if found:
        return QuoteCheck(verified=True, exact=True, score=100.0, multi=len(found) > 1, spans=found)
    norm_text = normalise(text)
    score = _partial(normalise(quote), norm_text)
    parts = fragments(quote)
    if len(parts) >= 2:
        # A stitched quote: every passage must be a close match on its own. The whole-quote score
        # is not enough, because a long genuine passage would carry a short invented one through.
        scores = [_partial(normalise(f), norm_text) for f in parts]
        if min(scores) >= fuzzy_threshold:
            return QuoteCheck(verified=True, exact=False, score=min(scores), multi=True)
        return QuoteCheck(verified=False, exact=False, score=min(score, min(scores)))
    if score >= fuzzy_threshold:
        return QuoteCheck(verified=True, exact=False, score=score)
    return QuoteCheck(verified=False, exact=False, score=score)
