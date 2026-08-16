import pytest

from app.teaching import detect_teaching
from app.local_answer import try_deterministic_answer
from app.db import engine as db_engine
from app.db import repository as db_repo


def test_detect_teaching_equals():
    result = detect_teaching("సహాయం = బాసట")
    assert result == {"standard_root": "సహాయం", "melimi_root": "బాసట"}


def test_detect_teaching_ignores_questions():
    assert detect_teaching("సమస్య అంటే ఏమిటి?") is None


def test_detect_teaching_assertive_statement():
    result = detect_teaching("సమస్య అంటే చిక్కు")
    assert result == {"standard_root": "సమస్య", "melimi_root": "చిక్కు"}


def test_detect_teaching_no_match():
    assert detect_teaching("నమస్కారం") is None


@pytest.mark.asyncio
async def test_deterministic_answer_known_word(monkeypatch):
    # Keep this unit test independent of external/database seed state while
    # still exercising the production deterministic-answer path.
    monkeypatch.setattr("app.local_answer.load_root_dictionary", lambda: {"సాయం": "తోడ్పాటు"})
    reply = await try_deterministic_answer("సాయం అంటే ఏమిటి?", "melimi", 0)
    assert reply is not None
    assert "తోడ్పాటు" in reply


@pytest.mark.asyncio
async def test_deterministic_answer_requires_no_history():
    reply = await try_deterministic_answer("సాయం అంటే ఏమిటి?", "melimi", 2)
    assert reply is None


@pytest.mark.asyncio
async def test_deterministic_answer_requires_melimi_mode():
    reply = await try_deterministic_answer("సాయం అంటే ఏమిటి?", "standard", 0)
    assert reply is None


@pytest.mark.asyncio
async def test_deterministic_answer_unknown_word(monkeypatch):
    monkeypatch.setattr("app.local_answer.load_root_dictionary", lambda: {})
    reply = await try_deterministic_answer("ఆకాశగంగ అంటే ఏమిటి?", "melimi", 0)
    assert reply is None


@pytest.mark.asyncio
async def test_db_layer_degrades_gracefully_without_database_url():
    # No DATABASE_URL configured in the test environment: every repository
    # call must return a safe empty value instead of raising.
    assert db_engine.is_configured() is False
    assert await db_engine.init_db() is False
    assert db_engine.is_available() is False

    assert await db_repo.get_cached_answer("melimi", "x", "v") is None
    assert await db_repo.lookup_approved("x") is None
    assert await db_repo.propose_candidate(standard_root="a", melimi_root="b") is None
    assert await db_repo.list_candidates() == []
    assert await db_repo.review_candidate(1, approve=True) is None
    assert await db_repo.candidate_stats() == {"enabled": False}
    assert await db_repo.recall_user_facts("u1") == []
