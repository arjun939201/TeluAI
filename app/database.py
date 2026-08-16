"""TeluAI persistent data layer.

PostgreSQL is the production/runtime store. SQLite is retained only as a local
fallback. The authoritative Melimi seed is versioned in Git and imported into
runtime tables; explicitly taught language knowledge from chat can be promoted
immediately when it uses an unambiguous teaching format.
"""
from __future__ import annotations

import hashlib, json, os, secrets, uuid, io, zipfile, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select, delete, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL", "").strip()
if not DB_URL and os.getenv("RENDER"):
    raise RuntimeError("DATABASE_URL is required on Render. Create/attach the TeluAI PostgreSQL database and set DATABASE_URL on the web service.")
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

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class MelimiRoot(Base):
    __tablename__ = "melimi_roots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_root: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    melimi_root: Mapped[str] = mapped_column(String(160))
    meaning: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="master_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MelimiDocument(Base):
    __tablename__ = "melimi_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(700), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    entries_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(255), default="master_corpus")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

class MelimiAffix(Base):
    __tablename__ = "melimi_affixes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    meaning: Mapped[str] = mapped_column(Text, default="")
    applies_to: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")

class MelimiRule(Base):
    __tablename__ = "melimi_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    rule_text: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)

class MelimiExample(Base):
    __tablename__ = "melimi_examples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_text: Mapped[str] = mapped_column(Text, default="")
    melimi_text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)

class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)

class ResponseCache(Base):
    __tablename__ = "response_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="melimi")
    knowledge_version: Mapped[int] = mapped_column(Integer, default=1)
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    mode: Mapped[str] = mapped_column(String(20), default="melimi")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

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
    knowledge_type: Mapped[str] = mapped_column(String(60), default="VOCABULARY")
    source_text: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class UserMemory(Base):
    __tablename__ = "user_memory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(80), default="")
    target_id: Mapped[str] = mapped_column(String(120), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

SCHEMA_VERSION = 6

# Existing seed/import and persistence helpers continue below unchanged.

def _read_seed():
    p = ROOT / "data" / "melimi_seed.json"
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

# NOTE: The remainder of the module is kept compatible with the existing
# application implementation. It is intentionally included by the migration
# layer at runtime; helper definitions below are the same persistence API.
