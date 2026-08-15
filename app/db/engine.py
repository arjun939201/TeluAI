"""Async Postgres engine bootstrap.

Every function here is defensive on purpose: TeluAI must keep working on
file/JSON storage alone if ``DATABASE_URL`` is unset, or if Postgres is
briefly unreachable. Nothing in this module ever raises out to the chat
pipeline — callers check ``is_available()`` and fall back automatically.
"""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger("teluai.db")

_engine = None
_session_factory = None
_available = False


def _normalize_url(url: str) -> str:
    """Render/Heroku-style 'postgres://...' URLs need the asyncpg driver
    spelled out for SQLAlchemy's async engine."""
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def is_configured() -> bool:
    return bool(settings.database_url.strip())


def is_available() -> bool:
    """True once init_db() has successfully connected and ensured the schema."""
    return _available


async def init_db() -> bool:
    """Create the async engine/session factory and the tables if needed.

    Safe to call multiple times (idempotent) and safe to call when Postgres
    isn't configured or isn't reachable yet — it just leaves the DB layer
    disabled and lets the rest of the app run on file-based storage.
    """
    global _engine, _session_factory, _available

    if not is_configured():
        _available = False
        return False

    if _available:
        return True

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.db.models import Base

        url = _normalize_url(settings.database_url)
        engine = create_async_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        _engine = engine
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
        _available = True
        logger.info("PostgreSQL connected and schema ensured.")
    except Exception as exc:  # noqa: BLE001 - deliberately broad; DB is optional
        logger.warning("PostgreSQL unavailable, continuing with file-based storage only: %s", exc)
        _engine = None
        _session_factory = None
        _available = False

    return _available


def session_scope():
    """Return a new AsyncSession context manager. Callers must check
    is_available() first — this raises if the DB was never initialized."""
    if _session_factory is None:
        raise RuntimeError("Database is not initialized or unavailable.")
    return _session_factory()


async def dispose() -> None:
    global _engine, _available
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _available = False
