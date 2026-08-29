"""Canonical application boundary for TeluAI conversation turns.

Request normalization, workspace-aware conversation resolution, context loading,
and prompt preparation live here. Transport middleware must not recreate these
business decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.workspace_service import LAB_WORKSPACE, create_workspace_conversation, normalize_workspace
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
    workspace: str = "main"


def _normalize_mode(value: Any) -> str:
    mode = str(value or "auto").strip().casefold()
    return mode if mode in {"auto", "standard", "melimi"} else "auto"


def _resolve_conversation(user_id: int, conversation_id: Any, message: str, mode: str, workspace: str) -> str:
    """Resolve a conversation exactly once at the application boundary."""
    if conversation_id:
        return ensure_conversation(user_id, str(conversation_id), message, mode, workspace)
    if workspace == LAB_WORKSPACE:
        return create_workspace_conversation(user_id, workspace, message, mode)
    return ensure_conversation(user_id, None, message, mode, workspace)


async def prepare_chat_turn(data: dict[str, Any], user: Any) -> PreparedChatTurn:
    """Prepare one chat turn through the single canonical application path."""
    message = str(data.get("message", "")).strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    requested_mode = _normalize_mode(data.get("mode"))
    workspace = normalize_workspace(data.get("workspace"))
    conversation_id = _resolve_conversation(
        user.id,
        data.get("conversation_id"),
        message,
        requested_mode,
        workspace,
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
    metadata = dict(metadata or {})
    metadata.setdefault("workspace", workspace)

    return PreparedChatTurn(
        message,
        conversation_id,
        history,
        decision,
        prompt,
        metadata,
        workspace,
    )
