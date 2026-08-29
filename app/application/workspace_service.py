"""Application-level workspace policy and conversation access."""
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
        return db.scalar(select(Conversation).where((Conversation.id == conversation_id) & (Conversation.user_id == user_id)))


def can_access_conversation(user_id: int, conversation_id: str, workspace: str) -> bool:
    return conversation_belongs_to_workspace(get_user_conversation(user_id, conversation_id), workspace)


def list_user_conversations(user_id: int, workspace: str) -> list[Conversation]:
    target_lab = normalize_workspace(workspace) == LAB_WORKSPACE
    with SessionLocal() as db:
        rows = db.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())).all()
    return [row for row in rows if is_lab_conversation(row) == target_lab]


def create_workspace_conversation(user_id: int, workspace: str, title: str, mode: str) -> str:
    """Create a conversation with an explicit workspace identity.

    The current schema predates a dedicated workspace column, so Lab identity
    remains encoded in the legacy title prefix until the schema migration adds
    the first-class field. All new callers should use this application API.
    """
    from app.database import create_conversation
    normalized = normalize_workspace(workspace)
    safe_title = " ".join(str(title or "").strip().split())[:70] or "New chat"
    if normalized == LAB_WORKSPACE and not safe_title.startswith(LAB_PREFIX):
        safe_title = LAB_PREFIX + safe_title
    return create_conversation(user_id, safe_title, "melimi" if normalized == LAB_WORKSPACE else mode)
