def run_migrations() -> None:
    # Startup schema creation must be non-recursive. The old init_db ->
    # run_migrations -> init_db cycle could prevent the server from starting.
    from app.database import Base, engine
    Base.metadata.create_all(engine)

    from app.language_space import install_routes
    from app.chat_learning import install_chat_learning
    from app.main import app

    install_chat_learning()
    if not getattr(app.state, "language_space_installed", False):
        install_routes(app)
        app.state.language_space_installed = True
