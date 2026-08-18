from __future__ import annotations
from sqlalchemy import text

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


def _apply_registered_migrations(engine):
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
        for version, statements in MIGRATIONS:
            if version in applied:
                continue
            for statement in statements:
                conn.execute(text(statement))
            conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:version)"), {"version": version})


def run_migrations():
    from app.database import Base, engine, UserSetting
    Base.metadata.create_all(engine)
    _apply_registered_migrations(engine)
    try:
        UserSetting.__table__.c.preferred_mode.default.arg = "auto"
    except Exception:
        pass
    from app.language_space import install_routes as install_language_space
    from app.chat_learning import install_chat_learning
    from app.melimi.registration_routes import install_routes as install_registration_routes
    from app.main import app
    install_chat_learning()
    if not getattr(app.state, "language_space_installed", False):
        install_language_space(app)
        app.state.language_space_installed = True
    install_registration_routes(app)
    if not getattr(app.state, "chat_overhaul_installed", False):
        from app.chat.middleware import ChatOverrideMiddleware
        # Starlette builds middleware_stack before lifespan. Resetting the lazy
        # stack here is safe during startup and lets the compatibility layer be
        # installed without changing the application factory in main.py.
        app.middleware_stack = None
        app.add_middleware(ChatOverrideMiddleware)
        app.state.chat_overhaul_installed = True
