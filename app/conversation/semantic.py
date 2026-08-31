"""Small, evidence-backed semantic carry-over state for conversation turns."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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


def semantic_context(facts: tuple[SemanticFact, ...]) -> dict[str, Any]:
    """Return JSON-safe semantic memory; candidates/guesses are intentionally excluded."""
    return {"facts": [asdict(fact) for fact in facts]}
