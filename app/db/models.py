"""SQLAlchemy models for TeluAI's PostgreSQL layer.

Three responsibilities live here, matching the local-first architecture:

- ``LearningCandidate`` — words/rules proposed during chat (or manually),
  awaiting human approval. Nothing here is ever treated as authoritative.
- ``ApprovedKnowledge`` — the human-approved Standard<->Melimi mappings that
  power deterministic (Tier 0, zero-Groq) answers.
- ``QueryCache`` — answers Groq has already produced for a given question +
  knowledge version, so repeated questions don't re-spend the free-tier
  token budget.
- ``UserMemoryItem`` — small, explicit per-user facts that persist across
  sessions/deploys instead of living only in client-sent chat history.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LearningCandidate(Base):
    __tablename__ = "learning_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), default="word")  # word | rule
    standard_root: Mapped[str] = mapped_column(String(256), default="")
    melimi_root: Mapped[str] = mapped_column(String(256), default="")
    meaning: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(32), default="chat")  # chat | manual | groq
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|approved|rejected
    proposed_message: Mapped[str] = mapped_column(Text, default="")
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped["dt.datetime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_learning_candidates_std_status", "standard_root", "status"),
    )


class ApprovedKnowledge(Base):
    __tablename__ = "approved_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    melimi: Mapped[str] = mapped_column(String(256), default="")
    root: Mapped[str] = mapped_column(String(256), default="")
    meaning: Mapped[str] = mapped_column(Text, default="")
    part_of_speech: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QueryCache(Base):
    __tablename__ = "query_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(16), default="standard")
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    knowledge_version: Mapped[str] = mapped_column(String(64), default="")
    hits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserMemoryItem(Base):
    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_user_memory_user_key", "user_id", "key", unique=True),
    )
