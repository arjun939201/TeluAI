"""Canonical application boundary for TeluAI conversation turns."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.workspace_service import create_workspace_conversation, normalize_workspace
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

    workspace = normalize_workspace(data.get("workspace"))
    conversation_id = data.get("conversation_id")
    if conversation_id:
        conversation_id = ensure_conversation(user.id, conversation_id, message, requested_mode, workspace)
    else:
        conversation_id = create_workspace_conversation(user.id, workspace, message, requested_mode)

    history, summary = context_for(user.id, conversation_id)
    if summary:
        history = [{"role": "system", "content": "Conversation summary: " + summary}] + history
    decision, prompt, metadata = prepare_prompt(
        message, requested_mode, history, user.id,
        response_length=str(data.get("response_length", "normal")),
    )
    return PreparedChatTurn(message, conversation_id, history, decision, prompt, metadata)
