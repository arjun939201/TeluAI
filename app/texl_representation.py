"""Structured, evidence-first representation produced by TEX-L."""
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
    lexical_equivalent: str | None
    regeneration_role: str | None
    confidence: str
    should_transhift: bool
    should_invent: bool
    boundaries: tuple[str, ...]


def classify_translation_intent(message: str) -> str:
    """Distinguish lexical naming questions from sentence translation."""
    text = " ".join(message.strip().split())
    lexical_markers = (
        "ఏమంటారు", "ఏమంటాం", "ఏమంటావు", "పదం ఏమిటి", "పదమేమిటి", "ఏ పదం",
    )
    translation_markers = ("అనువదించు", "అనువాదం", "తర్జుమా", "translate", "translation")
    if any(marker in text for marker in translation_markers):
        return "GRAMMATICAL_TRANSLATION"
    if any(marker in text for marker in lexical_markers):
        return "LEXICAL_EQUIVALENT"
    # A validated inflected lexical match used in a non-lexical utterance is
    # a sentence-level translation candidate. The grammatical form must still
    # be regenerated from validated morphology; it must not be copied blindly.
    return "UNSPECIFIED"


def represent_language(message: str, vocabulary=None) -> LanguageRepresentation:
    brain: BrainResult = analyze_language(message, vocabulary)
    evidence = tuple(
        TokenEvidence(item.token, item.canonical, item.melimi, item.relation,
                      item.confidence, item.authoritative)
        for item in brain.evidence
    )
    intent = classify_translation_intent(message)
    lexical = None
    if intent == "LEXICAL_EQUIVALENT":
        for item in evidence:
            if item.melimi and item.authoritative:
                lexical = item.melimi
                break
    return LanguageRepresentation(
        message=message,
        tokens=brain.analysis.tokens,
        evidence=evidence,
        decision=brain.decision,
        translation_intent=intent,
        lexical_equivalent=lexical,
        regeneration_role=None,
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
