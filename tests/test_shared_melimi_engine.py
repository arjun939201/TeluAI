import os

os.environ.pop("RENDER", None)
os.environ["CACHE_ENABLED"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_teluai_shared_language.sqlite3")

from app import database as db
from app.melimi.engine import build_language_engine_context


def _prepare_database():
    db.Base.metadata.create_all(bind=db.engine)


def test_melimi_head_contains_shared_understanding_and_generation_context():
    _prepare_database()
    context = build_language_engine_context(
        user_message="నమస్కారం",
        conversation_context="current turn",
        linguistic_analysis="internal analysis",
        response_plan="answer naturally",
        max_profile_chars=1200,
        max_relevant_chars=2400,
    )
    assert "MELIMI TELUGU UNDERSTANDING CONTEXT" in context
    assert "LANGUAGE GENERATION" in context
    assert "UNIFIED MELIMI LANGUAGE SPACE" in context
