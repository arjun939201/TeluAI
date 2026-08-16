from app.database import init_db


def run_migrations() -> None:
    init_db()
    # Install the unified language-space API and chat-learning hook after the
    # FastAPI application exists. The hook learns only explicit teaching syntax.
    from app.language_space import install_routes
    from app.chat_learning import install_chat_learning
    from app.main import app
    install_chat_learning()
    if not getattr(app.state, "language_space_installed", False):
        install_routes(app)
        app.state.language_space_installed = True
