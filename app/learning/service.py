from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.database import AuditLog, LearningCandidate, SessionLocal, add_learning_candidate, now
from app.language.publication import PublicationConflict, publish_root_candidate
from app.melimi.content_store import review_candidate as review_content_candidate


@dataclass(frozen=True)
class LearningSubmission:
    candidate_id: int
    knowledge_type: str
    status: str = "PENDING"


def submit_command_candidate(kind: str, payload: dict[str, Any], raw_text: str, user_id: int) -> LearningSubmission:
    if kind == "word":
        source = str(payload.get("source", "")).strip()
        melimi = str(payload.get("melimi", "")).strip()
        if not source or not melimi:
            raise ValueError("Both source and Melimi forms are required.")
        candidate_payload = {
            "source_root": source,
            "standard_root": source,
            "melimi_root": melimi,
            "melimi_equivalent": melimi,
            "meaning": "",
            "part_of_speech": "",
            "formation": "",
        }
        knowledge_type = "ROOT"
    elif kind == "content":
        content = str(payload.get("content", "")).strip()
        meaning = str(payload.get("meaning", "")).strip()
        if not content:
            raise ValueError("Content cannot be empty.")
        candidate_payload = {
            "title": "CHAT_COMMAND",
            "content": content,
            "meaning": meaning,
            "kind": "CONTENT",
        }
        knowledge_type = "CONTENT"
    else:
        raise ValueError("Unsupported language contribution type.")

    candidate_id = add_learning_candidate(user_id, knowledge_type, raw_text[:50000], candidate_payload)
    return LearningSubmission(candidate_id=candidate_id, knowledge_type=knowledge_type)


def _review_root_candidate(
    candidate_id: int,
    approve: bool,
    reviewer_note: str,
    reviewer_id: int | None,
):
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if candidate is None:
            return None
        if candidate.status != "PENDING":
            return {"id": candidate.id, "status": candidate.status, "payload": json.loads(candidate.payload_json or "{}")}

        payload = json.loads(candidate.payload_json or "{}")
        if approve:
            try:
                return publish_root_candidate(
                    db,
                    candidate,
                    payload,
                    reviewer_id=reviewer_id,
                    reviewer_note=reviewer_note,
                )
            except PublicationConflict as exc:
                candidate.status = "CONFLICT"
                candidate.reviewed_at = now()
                candidate.reviewer_user_id = reviewer_id
                candidate.review_note = reviewer_note[:10000]
                db.add(
                    AuditLog(
                        actor_user_id=reviewer_id,
                        action="language.publish_conflict",
                        target_type="learning_candidate",
                        target_id=str(candidate.id),
                        details_json=json.dumps(
                            {
                                "candidate_id": candidate.id,
                                "existing_melimi": exc.existing_melimi,
                                "payload": payload,
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
                db.commit()
                return {
                    "id": candidate.id,
                    "status": "CONFLICT",
                    "payload": payload,
                    "existing_melimi": exc.existing_melimi,
                }

        candidate.status = "REJECTED"
        candidate.reviewed_at = now()
        candidate.reviewer_user_id = reviewer_id
        candidate.review_note = reviewer_note[:10000]
        db.add(
            AuditLog(
                actor_user_id=reviewer_id,
                action="language.reject",
                target_type="learning_candidate",
                target_id=str(candidate.id),
                details_json=json.dumps(
                    {"candidate_id": candidate.id, "payload": payload, "review_note": reviewer_note[:10000]},
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        return {"id": candidate.id, "status": "REJECTED", "payload": payload}


def review_learning_candidate(
    candidate_id: int,
    approve: bool,
    reviewer_note: str = "",
    reviewer_id: int | None = None,
):
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if candidate is None:
            return None
        kind = candidate.knowledge_type

    if kind in {"CONTENT", "LANGUAGE_PACKAGE"}:
        return review_content_candidate(candidate_id, approve, reviewer_note)
    return _review_root_candidate(candidate_id, approve, reviewer_note, reviewer_id)
