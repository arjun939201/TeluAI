import os

os.environ.pop("RENDER", None)
os.environ["CACHE_ENABLED"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_teluai_shared_language.sqlite3")

from app import database as db
from app.melimi.language_service import analyze, build_understanding_context


def _prepare_database():
    db.Base.metadata.create_all(bind=db.engine)
    init = getattr(db, "init_db", None)
    if init:
        init()


def test_language_service_reads_shared_language_space():
    _prepare_database()
    result = analyze("నమస్కారం ఆసక్తికరమైన విషయం")
    assert "version" in result
    assert isinstance(result["tokens"], list)
    assert result["grammar"] is not None


def test_language_context_is_for_understanding_not_substitution():
    _prepare_database()
    context = build_understanding_context("నమస్కారం")
    assert "MELIMI TELUGU UNDERSTANDING CONTEXT" in context
    assert "language-space version" in context
    assert "RULE: MASTER language knowledge" in context
