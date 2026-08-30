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
    morphology: str | None
    grammatical_role: str | None
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
    return "UNSPECIFIED"


def _morphology_and_role(suffix: str) -> tuple[str | None, str | None]:
    """Map only the already validated engine suffix to a grammatical role.

    This is interpretation of an evidence-backed surface ending, not a
    productive rule for inventing new lexical forms.
    """
    if suffix in {"ాన్ని", "ను", "ని"}:
        return "accusative", "object"
    if suffix in {"ానికి", "కు", "కి"}:
        return "dative", "indirect_object"
    if suffix in {"తో"}:
        return "instrumental", "comitative_or_instrumental"
    if suffix in {"లో"}:
        return "locative", "locative"
    if suffix in {"నుండి", "నుంచి"}:
        return "ablative", "source"
    if suffix in {"యొక్క"}:
        return "genitive", "possessor"
    return (suffix or None), None


def represent_language(message: str, vocabulary=None) -> LanguageRepresentation:
    brain: BrainResult = analyze_language(message, vocabulary)
    intent = classify_translation_intent(message)
    evidence: list[TokenEvidence] = []

    for item in brain.matched:
        evidence.append(TokenEvidence(
            item["key"], item["key"], item.get("value"), "canonical",
            None, None, "high", True,
        ))

    for item in brain.inflected_matches:
        morphology, role = _morphology_and_role(item.get("suffix", ""))
        evidence.append(TokenEvidence(
            item["surface"], item["canonical"], item.get("target"),
            "validated_inflection", morphology, role, "high", True,
        ))

    for item in brain.family_candidates:
        evidence.append(TokenEvidence(
            item["word"], item["word"], item.get("target"), "family_candidate",
            None, None, "candidate", False,
        ))

    lexical = None
    if intent == "LEXICAL_EQUIVALENT":
        for item in evidence:
            if item.melimi and item.authoritative:
                lexical = item.melimi
                break

    regeneration_role = None
    if intent != "LEXICAL_EQUIVALENT":
        for item in evidence:
            if item.authoritative and item.grammatical_role:
                regeneration_role = item.grammatical_role
                break

    return LanguageRepresentation(
        message=message,
        tokens=brain.analysis.tokens,
        evidence=tuple(evidence),
        decision=brain.decision,
        translation_intent=intent,
        lexical_equivalent=lexical,
        regeneration_role=regeneration_role,
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
