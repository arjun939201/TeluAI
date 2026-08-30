"""Structured, evidence-first representation produced by TEX-L."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.texl_brain import BrainResult, LanguageEvidence, analyze_language


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
    text = " ".join(message.strip().split())
    lexical_markers = ("ఏమంటారు", "ఏమంటాం", "ఏమంటావు", "పదం ఏమిటి", "పదమేమిటి", "ఏ పదం")
    translation_markers = ("అనువదించు", "అనువాదం", "తర్జుమా", "translate", "translation")
    if any(marker in text for marker in translation_markers):
        return "GRAMMATICAL_TRANSLATION"
    if any(marker in text for marker in lexical_markers):
        return "LEXICAL_EQUIVALENT"
    return "UNSPECIFIED"


def _morphology_and_role(morphology: str | None) -> tuple[str | None, str | None]:
    if morphology == "accusative":
        return morphology, "object"
    if morphology == "dative":
        return morphology, "indirect_object"
    if morphology == "instrumental_comitative":
        return morphology, "comitative_or_instrumental"
    if morphology == "locative":
        return morphology, "locative"
    if morphology == "ablative":
        return morphology, "source"
    return morphology, None


def _to_token_evidence(item: LanguageEvidence) -> TokenEvidence:
    morphology, role = _morphology_and_role(item.morphology)
    return TokenEvidence(item.token, item.canonical, item.melimi, item.relation, morphology, role, item.confidence, item.authoritative)


def _ordered_evidence(brain: BrainResult) -> tuple[TokenEvidence, ...]:
    """Keep validated surface evidence ahead of its canonical fallback."""
    converted = tuple(_to_token_evidence(item) for item in brain.evidence)
    inflected = tuple(item for item in converted if item.relation == "validated_inflection")
    canonical = tuple(item for item in converted if item.relation != "validated_inflection")
    return inflected + canonical


def represent_language(message: str, vocabulary=None) -> LanguageRepresentation:
    brain: BrainResult = analyze_language(message, vocabulary)
    intent = classify_translation_intent(message)
    evidence = _ordered_evidence(brain)

    lexical = None
    if intent == "LEXICAL_EQUIVALENT":
        lexical = next((item.melimi for item in evidence if item.melimi and item.authoritative), None)

    regeneration_role = None
    if intent != "LEXICAL_EQUIVALENT":
        regeneration_role = next((item.grammatical_role for item in evidence if item.authoritative and item.grammatical_role), None)

    return LanguageRepresentation(message, brain.analysis.tokens, evidence, brain.decision, intent, lexical, regeneration_role, brain.analysis.confidence, brain.analysis.should_transhift, False, brain.analysis.boundaries)


def representation_context(message: str, vocabulary=None) -> dict[str, Any]:
    result = represent_language(message, vocabulary)
    context = asdict(result)
    context["tokens"] = list(result.tokens)
    context["evidence"] = [asdict(item) for item in result.evidence]
    context["boundaries"] = list(result.boundaries)
    return context
