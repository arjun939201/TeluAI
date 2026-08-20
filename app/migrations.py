from __future__ import annotations

from sqlalchemy import inspect, text

MIGRATIONS = [
    (1, (
        "CREATE INDEX IF NOT EXISTS ix_conversations_user_updated ON conversations (user_id, updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_messages_conversation_created ON messages (conversation_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_learning_candidates_status_created ON learning_candidates (status, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_knowledge_entries_status_kind ON knowledge_entries (status, kind)",
        "CREATE INDEX IF NOT EXISTS ix_melimi_roots_status_updated ON melimi_roots (status, updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_action ON audit_logs (created_at, action)",
        "CREATE INDEX IF NOT EXISTS ix_usage_user_created ON usage (user_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_user_memory_user_created ON user_memory (user_id, created_at)",
    )),
    (2, (
        "ALTER TABLE learning_candidates ADD COLUMN reviewer_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL",
        "ALTER TABLE learning_candidates ADD COLUMN review_note TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS ix_learning_candidates_reviewer ON learning_candidates (reviewer_user_id)",
    )),
]


def _column_exists(conn, table: str, column: str) -> bool:
    return any(item["name"] == column for item in inspect(conn).get_columns(table))


def _apply_registered_migrations(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
        for version, statements in MIGRATIONS:
            if version in applied:
                continue
            for statement in statements:
                if version == 2 and statement.startswith("ALTER TABLE learning_candidates ADD COLUMN reviewer_user_id"):
                    if _column_exists(conn, "learning_candidates", "reviewer_user_id"):
                        continue
                if version == 2 and statement.startswith("ALTER TABLE learning_candidates ADD COLUMN review_note"):
                    if _column_exists(conn, "learning_candidates", "review_note"):
                        continue
                conn.execute(text(statement))
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:version)"),
                {"version": version},
            )


def run_migrations():
    """Create/update database schema only.

    Runtime route registration, middleware composition and application wiring
    belong to the ASGI composition boundary, not the migration layer.
    """
    from app.database import Base, engine, UserSetting

    Base.metadata.create_all(engine)
    _apply_registered_migrations(engine)
    try:
        UserSetting.__table__.c.preferred_mode.default.arg = "auto"
    except Exception:
        pass
