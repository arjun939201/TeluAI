"""Evidence-first learning decisions for TeluAI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.teluai2_learning import LearningSuggestion, _valid_suggestion


@dataclass(frozen=True)
class LearningDecision:
    accepted: bool
    scope: str
    confidence: str
    reason: str


def assess_learning(suggestion: LearningSuggestion, *, role: str = "user", explicit: bool = True) -> LearningDecision:
    """Decide whether an extracted suggestion is safe to persist.

    Learning is opt-in and evidence-first: extraction alone never makes a fact
    authoritative. Owner/admin suggestions may enter shared knowledge;
    ordinary users remain isolated to their own learning scope.
    """
    if not explicit:
        return LearningDecision(False, "none", "low", "learning was not explicitly indicated")
    if not _valid_suggestion(suggestion):
        return LearningDecision(False, "none", "low", "suggestion failed validation")
    normalized_role = str(role or "user").strip().lower()
    if normalized_role == "owner":
        return LearningDecision(True, "global", "high", "explicit owner language knowledge")
    if normalized_role == "admin":
        return LearningDecision(True, "global", "high", "explicit approved-admin language knowledge")
    return LearningDecision(True, "user", "medium", "explicit user-scoped language suggestion")


def accepted_suggestions(suggestions: Iterable[LearningSuggestion], *, role: str = "user", explicit: bool = True) -> list[tuple[LearningSuggestion, LearningDecision]]:
    result = []
    for suggestion in suggestions:
        decision = assess_learning(suggestion, role=role, explicit=explicit)
        if decision.accepted:
            result.append((suggestion, decision))
    return result
