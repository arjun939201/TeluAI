"""Structured, evidence-first representation produced by TEX-L.

This module does not create linguistic knowledge. It turns the existing TEX-L
analysis into a stable intermediate representation that downstream retrieval,
context construction, TRANSHIFT, validation, and chat layers can consume.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.texl_brain import BrainResult, analyze_language


@dataclass(frozen=True)
class TokenEvidence:
    surface: str
    canonical: str | None
    melimi: str | None
    relation: str
    confidence: str
    authoritative: bool


@dataclass(frozen=True)
class LanguageRepresentation:
    message: str
    tokens: tuple[str, ...]
    evidence: tuple[TokenEvidence, ...]
    decision: str
    confidence: str
    should_transhift: bool
    should_invent: bool
    boundaries: tuple[str, ...]


def represent_language(message: str, vocabulary=None) -> LanguageRepresentation:
    """Convert the current TEX-L brain result into a stable IR.

    Canonical matches and validated inflections are authoritative evidence;
    family candidates remain explicitly non-authoritative. Unknown material is
    retained as surface input but is never converted into invented knowledge.
    """
    brain: BrainResult = analyze_language(message, vocabulary)
    evidence = tuple(
        TokenEvidence(
            surface=item.token,
            canonical=item.canonical,
            melimi=item.melimi,
            relation=item.relation,
            confidence=item.confidence,
            authoritative=item.authoritative,
        )
        for item in brain.evidence
    )
    return LanguageRepresentation(
        message=message,
        tokens=brain.analysis.tokens,
        evidence=evidence,
        decision=brain.decision,
        confidence=brain.analysis.confidence,
        should_transhift=brain.analysis.should_transhift,
        should_invent=False,
        boundaries=brain.analysis.boundaries,
    )


def representation_context(message: str, vocabulary=None) -> dict[str, Any]:
    """Return a compact JSON-safe representation for downstream AI context."""
    result = represent_language(message, vocabulary)
    return asdict(result)
