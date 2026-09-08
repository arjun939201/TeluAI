from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.learning.service as learning_service
from app.database import Base, KnowledgeVersion, LearningCandidate, MelimiRoot


@pytest.fixture
def isolated_learning_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(learning_service, "SessionLocal", Session)
    yield Session
    engine.dispose()


def test_submission_stays_pending_and_does_not_publish(isolated_learning_db):
    submission = learning_service.submit_command_candidate(
        "word",
        {"source": "ఇతర", "melimi": "కలివిడి"},
        "ఇతర = కలివిడి",
        123,
    )

    with isolated_learning_db() as db:
        candidate = db.get(LearningCandidate, submission.candidate_id)
        assert candidate is not None
        assert candidate.status == "PENDING"
        assert db.scalar(select(MelimiRoot)) is None
        assert db.scalar(select(KnowledgeVersion)) is None


def test_approval_publishes_master_with_version_and_reviewer(isolated_learning_db):
    submission = learning_service.submit_command_candidate(
        "word",
        {"source": "ఇతర", "melimi": "కలివిడి"},
        "ఇతర = కలివిడి",
        123,
    )

    result = learning_service.review_learning_candidate(
        submission.candidate_id,
        True,
        reviewer_note="validated linguistic evidence",
        reviewer_id=456,
    )

    assert result["status"] == "APPROVED"
    with isolated_learning_db() as db:
        candidate = db.get(LearningCandidate, submission.candidate_id)
        root = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == "ఇతర"))
        version = db.scalar(select(KnowledgeVersion))
        assert candidate.status == "APPROVED"
        assert candidate.reviewer_user_id == 456
        assert candidate.review_note == "validated linguistic evidence"
        assert root is not None
        assert root.melimi_root == "కలివిడి"
        assert root.status == "MASTER"
        assert version is not None
        assert version.source == "learning.approval"


def test_approval_cannot_overwrite_conflicting_master(isolated_learning_db):
    with isolated_learning_db() as db:
        db.add(MelimiRoot(standard_root="ఇతర", melimi_root="existing", status="MASTER", source="master_corpus"))
        db.commit()

    submission = learning_service.submit_command_candidate(
        "word",
        {"source": "ఇతర", "melimi": "కలివిడి"},
        "ఇతర = కలివిడి",
        123,
    )
    result = learning_service.review_learning_candidate(submission.candidate_id, True, reviewer_id=456)

    assert result["status"] == "CONFLICT"
    assert result["existing_melimi"] == "existing"
    with isolated_learning_db() as db:
        root = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == "ఇతర"))
        candidate = db.get(LearningCandidate, submission.candidate_id)
        assert root.melimi_root == "existing"
        assert candidate.status == "CONFLICT"
        assert db.scalar(select(KnowledgeVersion)) is None


def test_rejection_never_publishes(isolated_learning_db):
    submission = learning_service.submit_command_candidate(
        "word",
        {"source": "ఉపయోగించడం", "melimi": "వాడడం"},
        "ఉపయోగించడం = వాడడం",
        123,
    )
    result = learning_service.review_learning_candidate(
        submission.candidate_id,
        False,
        reviewer_note="insufficient evidence",
        reviewer_id=456,
    )

    assert result["status"] == "REJECTED"
    with isolated_learning_db() as db:
        candidate = db.get(LearningCandidate, submission.candidate_id)
        assert candidate.status == "REJECTED"
        assert candidate.reviewer_user_id == 456
        assert db.scalar(select(MelimiRoot)) is None
        assert db.scalar(select(KnowledgeVersion)) is None
