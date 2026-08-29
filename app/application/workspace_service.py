"""Canonical workspace policy and conversation access.

Workspace authorization belongs to the application layer. The frontend may
choose a workspace for presentation, but it is never the security boundary.
The current database schema stores Lab identity in a legacy title prefix; this
module keeps that compatibility detail in one place.
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
    if row is None:
        return False
    target_lab = normalize_workspace(workspace) == LAB_WORKSPACE
    return is_lab_conversation(row) == target_lab


def _workspace_clause(workspace: str):
    """Build the DB predicate used by all workspace-scoped reads."""
    if normalize_workspace(workspace) == LAB_WORKSPACE:
        return Conversation.title.like(f"{LAB_PREFIX}%")
    return ~Conversation.title.like(f"{LAB_PREFIX}%")


def get_user_conversation(user_id: int, conversation_id: str, workspace: str = MAIN_WORKSPACE) -> Conversation | None:
    with SessionLocal() as db:
        return db.scalar(
            select(Conversation).where(
                (Conversation.id == conversation_id)
                & (Conversation.user_id == user_id)
                & _workspace_clause(workspace)
            )
        )


def can_access_conversation(user_id: int, conversation_id: str, workspace: str) -> bool:
    return get_user_conversation(user_id, conversation_id, workspace) is not None


def list_user_conversations(user_id: int, workspace: str) -> list[Conversation]:
    with SessionLocal() as db:
        return db.scalars(
            select(Conversation)
            .where((Conversation.user_id == user_id) & _workspace_clause(workspace))
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        ).all()


def create_workspace_conversation(user_id: int, workspace: str, title: str, mode: str) -> str:
    """Create a conversation with an explicit application workspace identity."""
    from app.database import create_conversation

    normalized = normalize_workspace(workspace)
    safe_title = " ".join(str(title or "").strip().split())[:70] or "New chat"
    if normalized == LAB_WORKSPACE and not safe_title.startswith(LAB_PREFIX):
        safe_title = LAB_PREFIX + safe_title
    return create_conversation(user_id, safe_title, "melimi" if normalized == LAB_WORKSPACE else mode)
