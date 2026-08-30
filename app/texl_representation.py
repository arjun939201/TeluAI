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
    translation_intent: str
    confidence: str
    should_transhift: bool
    should_invent: bool
    boundaries: tuple[str, ...]


def classify_translation_intent(message: str) -> str:
    """Classify lexical-equivalence questions separately from translation.

    This is deliberately narrow. A question asking what a term is called in
    Melimi Telugu should return its lexical/canonical equivalent, rather than
    blindly reproducing the source surface case ending. A sentence that asks
    for translation remains grammatical-translation intent.
    """
    text = " ".join(message.strip().split())
    lexical_markers = (
        "ఏమంటారు",
        "ఏమంటాం",
        "ఏమంటావు",
        "అంటారు",
        "పదం ఏమిటి",
        "పదమేమిటి",
        "ఏ పదం",
    )
    translation_markers = (
        "అనువదించు",
        "అనువాదం",
        "తర్జుమా",
        "translate",
        "translation",
    )
    if any(marker in text for marker in translation_markers):
        return "GRAMMATICAL_TRANSLATION"
    if any(marker in text for marker in lexical_markers):
        return "LEXICAL_EQUIVALENT"
    return "UNSPECIFIED"


def represent_language(message: str, vocabulary=None) -> LanguageRepresentation:
    """Convert the current TEX-L brain result into a stable intermediate representation."""
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
        translation_intent=classify_translation_intent(message),
        confidence=brain.analysis.confidence,
        should_transhift=brain.analysis.should_transhift,
        should_invent=False,
        boundaries=brain.analysis.boundaries,
    )


def representation_context(message: str, vocabulary=None) -> dict[str, Any]:
    """Return a compact JSON-compatible representation for downstream AI context."""
    result = represent_language(message, vocabulary)
    context = asdict(result)
    context["tokens"] = list(result.tokens)
    context["evidence"] = [asdict(item) for item in result.evidence]
    context["boundaries"] = list(result.boundaries)
    return context
