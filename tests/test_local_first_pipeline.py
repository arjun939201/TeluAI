import pytest

from app.teaching import detect_teaching
from app.local_answer import try_deterministic_answer


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
