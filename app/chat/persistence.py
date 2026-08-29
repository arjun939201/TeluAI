from __future__ import annotations

from sqlalchemy import delete, select

from app.application.workspace_service import can_access_conversation
from app.database import Conversation, Message, SessionLocal, create_conversation, save_message


def ensure_conversation(user_id: int, conversation_id: str | None, message: str, mode: str) -> str:
    if conversation_id:
        with SessionLocal() as db:
            row = db.scalar(select(Conversation).where((Conversation.id == conversation_id) & (Conversation.user_id == user_id)))
            if not row:
                raise ValueError("Conversation not found.")
        return conversation_id
    return create_conversation(user_id, make_title(message), mode)


def make_title(message: str) -> str:
    text = " ".join((message or "").strip().split()).split("\n", 1)[0].rstrip("?!。！？")
    if not text:
        return "New chat"
    words = text.split()
    if len(words) > 9:
        text = " ".join(words[:9]) + "…"
    return text[:80]


def context_for(user_id: int, conversation_id: str, recent_limit: int = 16) -> tuple[list[dict], str]:
    with SessionLocal() as db:
        conversation = db.scalar(select(Conversation).where((Conversation.id == conversation_id) & (Conversation.user_id == user_id)))
        if not conversation:
            raise ValueError("Conversation not found.")
        rows = db.scalars(select(Message).where((Message.conversation_id == conversation_id) & (Message.user_id == user_id)).order_by(Message.created_at.desc(), Message.id.desc()).limit(recent_limit)).all()
        rows.reverse()
        return [{"role": row.role, "content": row.content} for row in rows if row.role in {"user", "assistant"}], conversation.summary or ""


def append_user_message(user_id: int, conversation_id: str, content: str) -> int:
    return save_message(user_id, conversation_id, "user", content)


def append_assistant_message(user_id: int, conversation_id: str, content: str, **metadata) -> int:
    return save_message(user_id, conversation_id, "assistant", content, **metadata)


def edit_user_message(user_id: int, message_id: int, content: str) -> str:
    with SessionLocal() as db:
        message = db.get(Message, message_id)
        if not message or message.user_id != user_id or message.role != "user":
            raise ValueError("User message not found.")
        conversation = db.scalar(select(Conversation).where((Conversation.id == message.conversation_id) & (Conversation.user_id == user_id)))
        if not conversation:
            raise ValueError("Conversation not found.")
        db.execute(delete(Message).where((Message.conversation_id == message.conversation_id) & (Message.id > message.id)))
        message.content = content.strip()
        conversation.updated_at = message.created_at
        db.commit()
        return conversation.id


def branch_from_message(user_id: int, message_id: int) -> tuple[str, str]:
    with SessionLocal() as db:
        target = db.get(Message, message_id)
        if not target or target.user_id != user_id:
            raise ValueError("Message not found.")
        user_message = target
        if target.role == "assistant":
            user_message = db.scalar(select(Message).where((Message.conversation_id == target.conversation_id) & (Message.user_id == user_id) & (Message.role == "user") & (Message.id < target.id)).order_by(Message.id.desc()))
        if not user_message:
            raise ValueError("No user message to regenerate.")
        conversation = db.scalar(select(Conversation).where((Conversation.id == target.conversation_id) & (Conversation.user_id == user_id)))
        if not conversation:
            raise ValueError("Conversation not found.")
        db.execute(delete(Message).where((Message.conversation_id == conversation.id) & (Message.id >= user_message.id)))
        conversation.updated_at = user_message.created_at
        content = user_message.content
        db.commit()
        return conversation.id, content
