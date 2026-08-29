"""Deterministic language lookup: authoritative data before generative AI."""
from __future__ import annotations

from dataclasses import dataclass

from teluai2.application.ports import Lexicon
from teluai2.domain.language import LookupResult


@dataclass(frozen=True)
class LookupAnswer:
    text: str
    result: LookupResult


def lookup_melimi(query: str, lexicon: Lexicon) -> LookupAnswer:
    cleaned = " ".join(query.split())
    if not cleaned:
        raise ValueError("A word or phrase is required")

    result = lexicon.lookup(cleaned)
    if result.matches and result.authoritative:
        primary = result.matches[0]
        text = primary.form
        if primary.meaning:
            text += f" — {primary.meaning}"
        return LookupAnswer(text=text, result=result)

    return LookupAnswer(
        text="No authoritative Melimi equivalent is currently established for this query.",
        result=result,
    )
