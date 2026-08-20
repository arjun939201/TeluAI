"""Atomic publication boundary for authoritative Melimi language roots.

A language publication is a single database transaction: candidate review,
authoritative root mutation, knowledge-version creation, and audit provenance
commit together or not at all. The publication boundary also serializes
concurrent language writers so two workers cannot allocate the same knowledge
version or race on the same root.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select, text

from app.database import AuditLog, KnowledgeVersion, LearningCandidate, MelimiRoot, now


class PublicationConflict(ValueError):
    """Raised when a candidate conflicts with an independently authoritative root."""

    def __init__(self, existing_melimi: str):
        super().__init__("The submitted language mapping conflicts with an existing authoritative mapping.")
        self.existing_melimi = existing_melimi


def _lock_publication(db, source: str) -> None:
    """Serialize language publications on PostgreSQL without a process-global lock."""
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"teluai:language-publication:{source.casefold()}"},
        )
    # SQLite has no equivalent cross-process advisory lock. Production uses
    # PostgreSQL; SQLite remains a single-process development/test fallback.


def _next_knowledge_version(db) -> int:
    latest = db.scalar(
        select(KnowledgeVersion.version)
        .order_by(KnowledgeVersion.version.desc())
        .limit(1)
        .with_for_update()
    )
    return int(latest or 0) + 1


def publish_root_candidate(
    db,
    candidate: LearningCandidate,
    payload: dict[str, Any],
    *,
    reviewer_id: int | None,
    reviewer_note: str = "",
):
    """Publish one ROOT/VOCABULARY candidate atomically.

    The caller owns the transaction. No commit occurs here, so candidate
    state, language authority, version, and audit provenance share one
    transaction boundary.
    """
    source = str(
        payload.get("source_root")
        or payload.get("standard_root")
        or payload.get("word")
        or ""
    ).strip()
    target = str(
        payload.get("melimi_root")
        or payload.get("melimi_equivalent")
        or ""
    ).strip().split("/")[0].strip()
    if not source or not target:
        raise ValueError("Both source and Melimi forms are required.")

    _lock_publication(db, source)

    existing = db.scalar(
        select(MelimiRoot)
        .where(MelimiRoot.standard_root == source)
        .with_for_update()
    )
    if existing and existing.melimi_root != target:
        raise PublicationConflict(existing.melimi_root)

    if existing:
        existing.melimi_root = target
        existing.meaning = str(payload.get("meaning", existing.meaning))
        existing.category = str(payload.get("part_of_speech", existing.category))
        existing.status = "MASTER"
        existing.source = "approved_chat_learning"
        existing.version += 1
        existing.updated_at = now()
        root_id = existing.id
    else:
        existing = MelimiRoot(
            standard_root=source,
            melimi_root=target,
            meaning=str(payload.get("meaning", "")),
            category=str(payload.get("part_of_speech", "")),
            status="MASTER",
            source="approved_chat_learning",
        )
        db.add(existing)
        db.flush()
        root_id = existing.id

    next_version = _next_knowledge_version(db)
    checksum = hashlib.sha256(
        json.dumps(
            {
                "candidate_id": candidate.id,
                "standard_root": source,
                "melimi_root": target,
                "reviewer_id": reviewer_id,
                "version": next_version,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    db.add(KnowledgeVersion(version=next_version, source="learning.approval", checksum=checksum))

    candidate.reviewed_at = now()
    candidate.reviewer_user_id = reviewer_id
    candidate.review_note = reviewer_note[:10000]
    candidate.status = "APPROVED"

    db.add(
        AuditLog(
            actor_user_id=reviewer_id,
            action="language.publish",
            target_type="melimi_root",
            target_id=str(root_id),
            details_json=json.dumps(
                {
                    "candidate_id": candidate.id,
                    "standard_root": source,
                    "melimi_root": target,
                    "knowledge_version": next_version,
                    "source": candidate.source_text,
                    "review_note": reviewer_note[:10000],
                },
                ensure_ascii=False,
            ),
        )
    )

    return {
        "id": candidate.id,
        "status": "APPROVED",
        "payload": payload,
        "root_id": root_id,
        "knowledge_version": next_version,
    }
