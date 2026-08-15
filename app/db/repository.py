"""Data-access functions for the Postgres layer.

Every function checks ``engine.is_available()`` first and returns a safe
empty/None value if the DB isn't up — nothing here should ever be able to
break the chat pipeline. Errors are logged, not raised.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from app.db import engine as db_engine

logger = logging.getLogger("teluai.db.repo")


# ---------------------------------------------------------------------------
# Response cache
# ---------------------------------------------------------------------------

def cache_key(mode: str, question: str, knowledge_version: str) -> str:
    raw = f"{mode}|{knowledge_version}|{question.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_cached_answer(mode: str, question: str, knowledge_version: str) -> Optional[str]:
    if not db_engine.is_available():
        return None
    from sqlalchemy import select

    from app.db.models import QueryCache

    key = cache_key(mode, question, knowledge_version)
    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(select(QueryCache).where(QueryCache.cache_key == key))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            row.hits += 1
            await session.commit()
            return row.answer
    except Exception:
        logger.exception("cache lookup failed")
        return None


async def set_cached_answer(mode: str, question: str, knowledge_version: str, answer: str) -> None:
    if not db_engine.is_available():
        return
    from sqlalchemy import select

    from app.db.models import QueryCache

    key = cache_key(mode, question, knowledge_version)
    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(select(QueryCache).where(QueryCache.cache_key == key))
            row = result.scalar_one_or_none()
            if row is None:
                session.add(QueryCache(
                    cache_key=key,
                    mode=mode,
                    question=question[:2000],
                    answer=answer,
                    knowledge_version=knowledge_version,
                ))
            else:
                row.answer = answer
                row.knowledge_version = knowledge_version
            await session.commit()
    except Exception:
        logger.exception("cache write failed")


# ---------------------------------------------------------------------------
# Approved knowledge (Tier 0 deterministic lookups)
# ---------------------------------------------------------------------------

async def lookup_approved(term: str) -> Optional[dict]:
    if not db_engine.is_available():
        return None
    term = (term or "").strip()
    if not term:
        return None
    from sqlalchemy import select

    from app.db.models import ApprovedKnowledge

    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(
                select(ApprovedKnowledge).where(
                    (ApprovedKnowledge.standard == term) | (ApprovedKnowledge.melimi == term)
                )
            )
            row = result.scalars().first()
            if row is None:
                return None
            return {
                "standard": row.standard,
                "melimi": row.melimi,
                "root": row.root,
                "meaning": row.meaning,
                "part_of_speech": row.part_of_speech,
                "note": row.note,
            }
    except Exception:
        logger.exception("approved lookup failed")
        return None


async def approved_count() -> int:
    if not db_engine.is_available():
        return 0
    from sqlalchemy import func, select

    from app.db.models import ApprovedKnowledge

    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(select(func.count()).select_from(ApprovedKnowledge))
            return int(result.scalar_one())
    except Exception:
        logger.exception("approved_count failed")
        return 0


# ---------------------------------------------------------------------------
# Learning candidates (pending -> approved/rejected review workflow)
# ---------------------------------------------------------------------------

async def propose_candidate(
    *,
    standard_root: str,
    melimi_root: str,
    meaning: str = "",
    note: str = "",
    source: str = "chat",
    kind: str = "word",
    proposed_message: str = "",
) -> Optional[int]:
    if not db_engine.is_available():
        return None
    standard_root = (standard_root or "").strip()
    melimi_root = (melimi_root or "").strip()
    if not standard_root and not melimi_root:
        return None

    from sqlalchemy import select

    from app.db.models import LearningCandidate

    try:
        async with db_engine.session_scope() as session:
            existing = await session.execute(
                select(LearningCandidate).where(
                    LearningCandidate.standard_root == standard_root,
                    LearningCandidate.melimi_root == melimi_root,
                    LearningCandidate.status == "pending",
                )
            )
            if existing.scalars().first():
                return None  # already awaiting review, don't duplicate

            candidate = LearningCandidate(
                kind=kind,
                standard_root=standard_root,
                melimi_root=melimi_root,
                meaning=meaning[:2000],
                note=note[:2000],
                source=source,
                proposed_message=proposed_message[:2000],
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            return candidate.id
    except Exception:
        logger.exception("propose_candidate failed")
        return None


def _candidate_to_dict(row) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "standard_root": row.standard_root,
        "melimi_root": row.melimi_root,
        "meaning": row.meaning,
        "note": row.note,
        "source": row.source,
        "status": row.status,
        "proposed_message": row.proposed_message,
        "reviewer_note": row.reviewer_note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


async def list_candidates(status: str = "pending", limit: int = 100) -> list[dict]:
    if not db_engine.is_available():
        return []
    from sqlalchemy import select

    from app.db.models import LearningCandidate

    try:
        async with db_engine.session_scope() as session:
            q = select(LearningCandidate).order_by(LearningCandidate.created_at.desc()).limit(limit)
            if status and status != "all":
                q = q.where(LearningCandidate.status == status)
            result = await session.execute(q)
            return [_candidate_to_dict(r) for r in result.scalars().all()]
    except Exception:
        logger.exception("list_candidates failed")
        return []


async def review_candidate(candidate_id: int, *, approve: bool, reviewer_note: str = "") -> Optional[dict]:
    if not db_engine.is_available():
        return None
    from sqlalchemy import select

    from app.db.models import ApprovedKnowledge, LearningCandidate

    try:
        async with db_engine.session_scope() as session:
            row = await session.get(LearningCandidate, candidate_id)
            if row is None:
                return None

            row.status = "approved" if approve else "rejected"
            row.reviewer_note = reviewer_note[:2000]
            row.reviewed_at = datetime.now(timezone.utc)

            if approve and row.standard_root and row.melimi_root:
                existing = await session.execute(
                    select(ApprovedKnowledge).where(ApprovedKnowledge.standard == row.standard_root)
                )
                approved_row = existing.scalars().first()
                if approved_row is None:
                    session.add(ApprovedKnowledge(
                        standard=row.standard_root,
                        melimi=row.melimi_root,
                        meaning=row.meaning,
                        note=row.note,
                    ))
                else:
                    approved_row.melimi = row.melimi_root
                    approved_row.meaning = row.meaning or approved_row.meaning
                    approved_row.note = row.note or approved_row.note

            await session.commit()
            await session.refresh(row)
            return _candidate_to_dict(row)
    except Exception:
        logger.exception("review_candidate failed")
        return None


async def candidate_stats() -> dict:
    if not db_engine.is_available():
        return {"enabled": False}
    from sqlalchemy import func, select

    from app.db.models import LearningCandidate

    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(
                select(LearningCandidate.status, func.count()).group_by(LearningCandidate.status)
            )
            counts = {status: count for status, count in result.all()}
        return {
            "enabled": True,
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
            "approved_knowledge_entries": await approved_count(),
        }
    except Exception:
        logger.exception("candidate_stats failed")
        return {"enabled": True, "error": "stats query failed"}


# ---------------------------------------------------------------------------
# Per-user memory (persists across sessions, unlike client-sent history)
# ---------------------------------------------------------------------------

async def remember_user_fact(user_id: str, key: str, value: str) -> None:
    if not db_engine.is_available() or not user_id:
        return
    from sqlalchemy import select

    from app.db.models import UserMemoryItem

    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(
                select(UserMemoryItem).where(UserMemoryItem.user_id == user_id, UserMemoryItem.key == key)
            )
            row = result.scalars().first()
            if row is None:
                session.add(UserMemoryItem(user_id=user_id, key=key, value=value[:4000]))
            else:
                row.value = value[:4000]
            await session.commit()
    except Exception:
        logger.exception("remember_user_fact failed")


async def recall_user_facts(user_id: str, limit: int = 20) -> list[dict]:
    if not db_engine.is_available() or not user_id:
        return []
    from sqlalchemy import select

    from app.db.models import UserMemoryItem

    try:
        async with db_engine.session_scope() as session:
            result = await session.execute(
                select(UserMemoryItem)
                .where(UserMemoryItem.user_id == user_id)
                .order_by(UserMemoryItem.created_at.desc())
                .limit(limit)
            )
            return [{"key": r.key, "value": r.value} for r in result.scalars().all()]
    except Exception:
        logger.exception("recall_user_facts failed")
        return []
