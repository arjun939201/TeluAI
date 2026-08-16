from app.database import init_db


def run_migrations() -> None:
    init_db()
    # The language-space routes are installed after the FastAPI application
    # exists. Keeping them here avoids coupling the content layer to app/main.py.
    from app.language_space import install_routes
    from app.main import app
    if not getattr(app.state, "language_space_installed", False):
        install_routes(app)
        app.state.language_space_installed = True
