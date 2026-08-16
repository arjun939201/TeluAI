"""Runtime compatibility bridge for PostgreSQL-backed Melimi content.

The current application imports persistence functions directly from app.database.
This module swaps only the language-content paths before app.main is imported,
so the existing architecture remains intact while language content moves out
of Git and into PostgreSQL.
"""
from __future__ import annotations

from app import database as db
from app.melimi import content_store


def _content_candidate_or_approved(user_id, knowledge_type, source_text, payload):
    if knowledge_type == "CONTENT" and isinstance(payload, dict):
        user = None
        if user_id is not None:
            with db.SessionLocal() as session:
                user = session.get(db.User, user_id)
        approved = bool(user and user.role in {"owner", "admin"})
        result = content_store.submit_content(
            user_id or 0,
            str(payload.get("title", "")),
            str(payload.get("content", "")),
            approved=approved,
        )
        return result.get("candidate_id", 0)
    return _original_add_learning_candidate(user_id, knowledge_type, source_text, payload)


def apply() -> None:
    global _original_add_learning_candidate
    _original_add_learning_candidate = db.add_learning_candidate

    # Git is no longer an authoritative Melimi data source.
    db._read_seed = lambda: {}
    db._seed_language = lambda: None

    # New ingestion/approval layer for uploaded language content.
    db.ingest_language_package = content_store.ingest_language_package
    db.review_candidate = content_store.review_candidate
    db.add_learning_candidate = _content_candidate_or_approved


apply()
