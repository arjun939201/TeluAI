"""Coherent TEX-L language-brain orchestration.

This layer composes existing evidence-backed capabilities without turning
surface similarity into a linguistic rule. It is intentionally conservative:
unknown analyses remain uncertain and never become vocabulary automatically.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from app.melimi_engine import analyze, MelimiAnalysis


@dataclass(frozen=True)
class LanguageEvidence:
    token: str
    canonical: str | None
    melimi: str | None
    relation: str
    confidence: str
    authoritative: bool


@dataclass(frozen=True)
class BrainResult:
    analysis: MelimiAnalysis
    evidence: tuple[LanguageEvidence, ...]
    decision: str


def analyze_language(message: str, vocabulary=None) -> BrainResult:
    """Run TEX-L's conservative lexical brain over a message.

    The vocabulary source remains authoritative. Inflected surfaces resolve to
    canonical entries; family candidates are reported as candidates only.
    """
    result = analyze(message, vocabulary) if vocabulary is not None else analyze(message)
    evidence: list[LanguageEvidence] = []
    for item in result.matched:
        evidence.append(LanguageEvidence(item["key"], item["key"], item.get("value"), "canonical", "high", True))
    for item in result.inflected_matches:
        evidence.append(LanguageEvidence(item["surface"], item["canonical"], item.get("target"), "validated_inflection", "high", True))
    for item in result.family_candidates:
        evidence.append(LanguageEvidence(item["word"], item["word"], item.get("target"), "family_candidate", "candidate", False))
    if result.should_transhift:
        decision = "RESOLVE_CANONICAL"
    elif result.family_candidates:
        decision = "REVIEW_FAMILY"
    else:
        decision = "UNKNOWN_NO_INVENTION"
    return BrainResult(result, tuple(evidence), decision)


def compact_brain_report(message: str, vocabulary=None) -> dict:
    """Machine/UI-safe compact representation of a TEX-L decision."""
    result = analyze_language(message, vocabulary)
    return {
        "decision": result.decision,
        "confidence": result.analysis.confidence,
        "should_transhift": result.analysis.should_transhift,
        "should_invent": False,
        "evidence": [asdict(x) for x in result.evidence],
        "boundaries": list(result.analysis.boundaries),
    }
