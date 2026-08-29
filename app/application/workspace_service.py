"""Application-level workspace policy and conversation access.

This module is deliberately small: API/middleware code asks the application
layer what a user may see or access, while persistence remains in the database
module.  Workspace isolation is therefore a product rule, not a frontend hack.
"""
from __future__ import annotations

from sqlalchemy import select

from app.database import Conversation, SessionLocal

LAB_PREFIX = "[Melimi Lab] "
MAIN_WORKSPACE = "main"
LAB_WORKSPACE = "lab"


def normalize_workspace(value: str | None) -> str:
    return LAB_WORKSPACE if str(value or "").strip().casefold() == LAB_WORKSPACE else MAIN_WORKSPACE


def is_lab_conversation(row: Conversation | None) -> bool:
    return bool(row and str(row.title or "").startswith(LAB_PREFIX))


def conversation_belongs_to_workspace(row: Conversation | None, workspace: str) -> bool:
    return bool(row) and is_lab_conversation(row) == (normalize_workspace(workspace) == LAB_WORKSPACE)


def get_user_conversation(user_id: int, conversation_id: str) -> Conversation | None:
    with SessionLocal() as db:
        return db.scalar(
            select(Conversation).where(
                (Conversation.id == conversation_id) & (Conversation.user_id == user_id)
            )
        )


def can_access_conversation(user_id: int, conversation_id: str, workspace: str) -> bool:
    return conversation_belongs_to_workspace(
        get_user_conversation(user_id, conversation_id), workspace
    )


def list_user_conversations(user_id: int, workspace: str) -> list[Conversation]:
    target_lab = normalize_workspace(workspace) == LAB_WORKSPACE
    with SessionLocal() as db:
        rows = db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        ).all()
    return [row for row in rows if is_lab_conversation(row) == target_lab]
