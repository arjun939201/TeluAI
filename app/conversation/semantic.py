"""Evidence-backed semantic carry-over state for conversation turns."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SemanticFact:
    surface: str
    canonical: str | None
    melimi: str | None
    grammatical_role: str | None
    authoritative: bool
    confidence: str


def facts_from_representation(representation: dict[str, Any]) -> tuple[SemanticFact, ...]:
    """Extract only validated/authoritative TEX-L evidence for later turns."""
    facts: list[SemanticFact] = []
    for item in representation.get("evidence", []):
        if not isinstance(item, dict) or not item.get("authoritative"):
            continue
        canonical = item.get("canonical")
        melimi = item.get("melimi")
        if not canonical and not melimi:
            continue
        facts.append(SemanticFact(
            surface=item.get("surface", ""),
            canonical=canonical,
            melimi=melimi,
            grammatical_role=item.get("grammatical_role"),
            authoritative=True,
            confidence=item.get("confidence", "unknown"),
        ))
    return tuple(facts)


def merge_facts(existing: Iterable[SemanticFact], new: Iterable[SemanticFact], limit: int = 32) -> tuple[SemanticFact, ...]:
    """Merge semantic facts deterministically, keeping the newest evidence for a surface/canonical pair."""
    merged: dict[tuple[str, str | None, str | None], SemanticFact] = {}
    for fact in list(existing) + list(new):
        if not fact.authoritative:
            continue
        key = (fact.surface, fact.canonical, fact.melimi)
        merged[key] = fact
    return tuple(list(merged.values())[-limit:])


def retrieve_facts(facts: Iterable[SemanticFact], surface: str | None = None, canonical: str | None = None) -> tuple[SemanticFact, ...]:
    """Retrieve relevant persisted meaning without inventing or rewriting facts."""
    requested_surface = (surface or "").strip()
    requested_canonical = (canonical or "").strip()
    if not requested_surface and not requested_canonical:
        return tuple()
    matches = []
    for fact in facts:
        if requested_surface and fact.surface == requested_surface:
            matches.append(fact)
        elif requested_canonical and (fact.canonical == requested_canonical or fact.melimi == requested_canonical):
            matches.append(fact)
    return tuple(matches)


def semantic_context(facts: tuple[SemanticFact, ...]) -> dict[str, Any]:
    """Return JSON-safe semantic memory; candidates/guesses are intentionally excluded."""
    return {"facts": [asdict(fact) for fact in facts]}
