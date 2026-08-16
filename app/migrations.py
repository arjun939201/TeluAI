def run_migrations() -> None:
    # Keep startup schema creation non-recursive. app.main calls this after the
    # FastAPI app exists; database.init_db is intentionally not called here.
    from app.database import Base, engine
    Base.metadata.create_all(engine)

    from app.language_space import install_routes
    from app.chat_learning import install_chat_learning
    from app.main import app
    install_chat_learning()
    if not getattr(app.state, "language_space_installed", False):
        install_routes(app)
        app.state.language_space_installed = True
