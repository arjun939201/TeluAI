"""Small, serializable semantic state for cross-turn conversation carry-over."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SemanticEntity:
    canonical: str
    surface: str
    melimi: str | None = None
    grammatical_role: str | None = None
    authoritative: bool = False
    confidence: str = "unknown"


def entities_from_language_representation(representation: dict[str, Any]) -> tuple[SemanticEntity, ...]:
    """Extract only validated/authoritative semantic evidence from TEX-L output."""
    entities: list[SemanticEntity] = []
    for item in representation.get("evidence", []) or []:
        if not isinstance(item, dict):
            continue
        canonical = item.get("canonical")
        if not canonical or item.get("authoritative") is not True:
            continue
        entities.append(SemanticEntity(
            canonical=canonical,
            surface=item.get("surface") or canonical,
            melimi=item.get("melimi"),
            grammatical_role=item.get("grammatical_role"),
            authoritative=True,
            confidence=item.get("confidence", "unknown"),
        ))
    return tuple(entities)


def semantic_context(entities: tuple[SemanticEntity, ...]) -> dict[str, Any]:
    """Return JSON-safe semantic carry-over state for internal conversation context."""
    return {"entities": [asdict(entity) for entity in entities]}
