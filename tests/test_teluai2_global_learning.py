from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import teluai2_learning
from app.teluai2_learning import LearningSuggestion, learned_global, remember_suggestion


def _isolated_engine(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(teluai2_learning, "engine", engine)
    return engine


def test_owner_learning_is_shared(monkeypatch):
    _isolated_engine(monkeypatch)
    remember_suggestion(1, LearningSuggestion("VOCABULARY", "సంతోషం", "అలరిక", "owner teaching"), "owner")
    assert any(item["key"] == "సంతోషం" and item["value"] == "అలరిక" for item in learned_global())


def test_approved_admin_learning_is_shared(monkeypatch):
    _isolated_engine(monkeypatch)
    remember_suggestion(2, LearningSuggestion("VOCABULARY", "ఆనందం", "ఉల్లాసం", "admin teaching"), "admin")
    assert any(item["key"] == "ఆనందం" and item["value"] == "ఉల్లాసం" for item in learned_global())


def test_global_memory_is_not_written_for_normal_user(monkeypatch):
    _isolated_engine(monkeypatch)
    # UserMemory uses the application's normal database; this test only asserts
    # that the shared table is untouched by an ordinary-user role.
    remember_suggestion(3, LearningSuggestion("VOCABULARY", "దుఃఖం", "విషాదం", "user teaching"), "user")
    assert not any(item["key"] == "దుఃఖం" for item in learned_global())
