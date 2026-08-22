"""Canonical application boundary for TeluAI conversation turns.

HTTP/middleware code should not own conversation orchestration. This module
coordinates conversation persistence/context with the existing prompt service
and returns a typed turn object for the runtime transport layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.chat.persistence import context_for, ensure_conversation
from app.chat.service import prepare_prompt


@dataclass(frozen=True)
class PreparedChatTurn:
    message: str
    conversation_id: str
    history: list[dict[str, Any]]
    decision: Any
    prompt: str
    metadata: dict[str, Any]


async def prepare_chat_turn(data: dict[str, Any], user: Any) -> PreparedChatTurn:
    """Prepare one chat turn through the canonical application path."""
    message = str(data.get("message", "")).strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    requested_mode = str(data.get("mode", "auto"))
    if requested_mode not in {"auto", "standard", "melimi"}:
        requested_mode = "auto"

    conversation_id = ensure_conversation(
        user.id,
        data.get("conversation_id"),
        message,
        requested_mode,
    )
    history, summary = context_for(user.id, conversation_id)
    if summary:
        history = [{"role": "system", "content": "Conversation summary: " + summary}] + history

    decision, prompt, metadata = prepare_prompt(
        message,
        requested_mode,
        history,
        user.id,
        response_length=str(data.get("response_length", "normal")),
    )
    return PreparedChatTurn(
        message=message,
        conversation_id=conversation_id,
        history=history,
        decision=decision,
        prompt=prompt,
        metadata=metadata,
    )
