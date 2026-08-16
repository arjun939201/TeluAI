from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.database import LearningCandidate, SessionLocal, add_learning_candidate, review_candidate as review_root_candidate
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


def review_learning_candidate(candidate_id: int, approve: bool, reviewer_note: str = "", reviewer_id: int | None = None):
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if candidate is None:
            return None
        kind = candidate.knowledge_type

    if kind in {"CONTENT", "LANGUAGE_PACKAGE"}:
        result = review_content_candidate(candidate_id, approve, reviewer_note)
    else:
        result = review_root_candidate(candidate_id, approve, reviewer_note)

    if result is None:
        return None

    # The underlying stores currently keep reviewer details in their payload
    # for compatibility. This service also preserves the review actor in the
    # audit layer at the API boundary.
    return result
