"""Persistent TeluAI data layer.

PostgreSQL is used when DATABASE_URL is configured (Render production).
SQLite is retained as a local development fallback so the language engine can
still be run without an online database.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, MetaData, String, Text, create_engine,
    select, update, delete, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL", "").strip()
if DB_URL.startswith("postgres://"):
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgres://"):]
elif DB_URL.startswith("postgresql://"):
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgresql://"):]

if not DB_URL:
    local_path = ROOT / "data" / "teluai.sqlite3"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    DB_URL = f"sqlite:///{local_path}"

connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    mode: Mapped[str] = mapped_column(String(20), default="melimi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class UserSetting(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferred_mode: Mapped[str] = mapped_column(String(20), default="melimi")
    response_length: Mapped[str] = mapped_column(String(20), default="normal")
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class LearningCandidate(Base):
    __tablename__ = "learning_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    knowledge_type: Mapped[str] = mapped_column(String(40), default="VOCABULARY")
    source_text: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserMemory(Base):
    __tablename__ = "user_memory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


SCHEMA_VERSION = 1

def init_db() -> None:
    Base.metadata.create_all(engine)
    # Keep a tiny version table so future schema changes can be migrated
    # deliberately instead of silently changing the schema at runtime.
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM schema_version").scalar()
        if not count:
            conn.exec_driver_sql("INSERT INTO schema_version(version) VALUES (1)")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return "pbkdf2_sha256$260000$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def create_user(username: str, email: str, password: str) -> User:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        if db.scalar(select(User).where((User.username == username) | (User.email == email))):
            raise ValueError("Username or email is already registered.")
        user = User(username=username, email=email, password_hash=_hash_password(password), created_at=now)
        db.add(user)
        db.flush()
        db.add(UserSetting(user_id=user.id))
        db.commit()
        return user


def authenticate(email_or_username: str, password: str) -> User | None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where((User.email == email_or_username) | (User.username == email_or_username)))
        if not user or not verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        return user


def create_session(user_id: int, days: int = 30) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:
        db.add(Session(token_hash=token_hash, user_id=user_id, expires_at=datetime.now(timezone.utc) + timedelta(days=days)))
        db.commit()
    return raw


def user_from_session(raw: str | None) -> User | None:
    if not raw:
        return None
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:
        row = db.scalar(select(Session).where(Session.token_hash == token_hash))
        if not row:
            return None
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
        return db.get(User, row.user_id)


def delete_session(raw: str | None) -> None:
    if not raw:
        return
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:
        db.execute(delete(Session).where(Session.token_hash == token_hash))
        db.commit()


def create_conversation(user_id: int, title: str, mode: str) -> str:
    import uuid
    now = datetime.now(timezone.utc)
    cid = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(Conversation(id=cid, user_id=user_id, title=title[:200] or "New chat", mode=mode, created_at=now, updated_at=now))
        db.commit()
    return cid


def save_message(user_id: int, conversation_id: str, role: str, content: str, model: str | None = None, input_tokens: int | None = None, output_tokens: int | None = None, latency_ms: int | None = None) -> int:
    with SessionLocal() as db:
        conv = db.scalar(select(Conversation).where((Conversation.id == conversation_id) & (Conversation.user_id == user_id)))
        if not conv:
            raise ValueError("Conversation not found.")
        msg = Message(user_id=user_id, conversation_id=conversation_id, role=role, content=content, model=model, input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=latency_ms)
        db.add(msg)
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        return msg.id


def get_conversations(user_id: int) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = db.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())).all()
        return [{"id": r.id, "title": r.title, "mode": r.mode, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()} for r in rows]


def get_history(user_id: int, conversation_id: str, limit: int = 40) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        conv = db.scalar(select(Conversation).where((Conversation.id == conversation_id) & (Conversation.user_id == user_id)))
        if not conv:
            raise ValueError("Conversation not found.")
        rows = db.scalars(select(Message).where((Message.conversation_id == conversation_id) & (Message.user_id == user_id)).order_by(Message.created_at.desc()).limit(limit)).all()
        rows.reverse()
        return [{"id": r.id, "role": r.role, "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]


def add_learning_candidate(user_id: int | None, knowledge_type: str, source_text: str, payload: dict[str, Any]) -> int:
    with SessionLocal() as db:
        item = LearningCandidate(user_id=user_id, knowledge_type=knowledge_type, source_text=source_text, payload_json=json.dumps(payload, ensure_ascii=False), status="PENDING")
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id


def save_usage(user_id: int | None, model: str | None, input_tokens: int | None, output_tokens: int | None, status: str = "ok") -> None:
    with SessionLocal() as db:
        db.add(Usage(user_id=user_id, model=model, input_tokens=input_tokens, output_tokens=output_tokens, status=status))
        db.commit()


def list_candidates(status: str = "PENDING") -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = db.scalars(select(LearningCandidate).where(LearningCandidate.status == status).order_by(LearningCandidate.created_at.desc())).all()
        return [{"id": r.id, "user_id": r.user_id, "knowledge_type": r.knowledge_type, "source_text": r.source_text, "payload": json.loads(r.payload_json or "{}"), "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]

def review_candidate(candidate_id: int, approve: bool, reviewer_note: str = "") -> dict[str, Any] | None:
    with SessionLocal() as db:
        row = db.get(LearningCandidate, candidate_id)
        if not row:
            return None
        row.status = "APPROVED" if approve else "REJECTED"
        row.reviewed_at = datetime.now(timezone.utc)
        if reviewer_note:
            payload = json.loads(row.payload_json or "{}")
            payload["reviewer_note"] = reviewer_note
            row.payload_json = json.dumps(payload, ensure_ascii=False)
        db.commit()
        return {"id": row.id, "status": row.status, "payload": json.loads(row.payload_json or "{}") }

def approved_learning() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = db.scalars(select(LearningCandidate).where(LearningCandidate.status == "APPROVED").order_by(LearningCandidate.created_at.asc())).all()
        return [json.loads(r.payload_json or "{}") | {"knowledge_type": r.knowledge_type} for r in rows]

def remember_user_memory(user_id: int, key: str, value: str) -> None:
    with SessionLocal() as db:
        row = db.scalar(select(UserMemory).where((UserMemory.user_id == user_id) & (UserMemory.key == key)))
        if row:
            row.value = value
        else:
            db.add(UserMemory(user_id=user_id, key=key, value=value))
        db.commit()

def recall_user_memory(user_id: int, limit: int = 12) -> list[dict[str, str]]:
    with SessionLocal() as db:
        rows = db.scalars(select(UserMemory).where(UserMemory.user_id == user_id).order_by(UserMemory.created_at.desc()).limit(limit)).all()
        return [{"key": r.key, "value": r.value} for r in rows]
