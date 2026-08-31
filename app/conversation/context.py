"""Context selection and budgeting for conversation reasoning."""
from __future__ import annotations

from typing import Iterable

from app.conversation.state import ConversationState, Turn


def select_context(state: ConversationState, *, max_turns: int | None = None, max_chars: int = 12000) -> list[Turn]:
    """Select the most relevant bounded recent context without mutating state."""
    turns = list(state.recent)
    if max_turns is not None:
        turns = turns[-max(0, max_turns):]
    if max_chars <= 0:
        return []

    selected: list[Turn] = []
    used = 0
    for turn in reversed(turns):
        cost = len(turn.content) + len(turn.role) + 2
        if selected and used + cost > max_chars:
            break
        if not selected and cost > max_chars:
            selected.append(Turn(turn.role, turn.content[:max_chars]))
            break
        selected.append(turn)
        used += cost
    return list(reversed(selected))


def context_budget(state: ConversationState, *, max_turns: int | None = None, max_chars: int = 12000) -> dict:
    """Return selected conversation context and stable budgeting metadata."""
    turns = select_context(state, max_turns=max_turns, max_chars=max_chars)
    return {
        "turns": [{"role": turn.role, "content": turn.content} for turn in turns],
        "turn_count": len(turns),
        "char_count": sum(len(turn.content) for turn in turns),
        "max_chars": max_chars,
    }
