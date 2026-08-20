"""Production ASGI composition boundary for TeluAI.

Database migrations are schema-only. Runtime routes, chat behavior and the
Melimi Lab are composed explicitly here so importing or migrating the database
cannot mutate FastAPI application behavior.
"""
from app.main import app
from app.chat.middleware import ChatOverrideMiddleware
from app.chat_learning import install_chat_learning
from app.language_space import install_routes as install_language_space
from app.melimi.registration_routes import install_routes as install_registration_routes


# Runtime application composition belongs at the ASGI boundary.
install_chat_learning()
if not getattr(app.state, "language_space_installed", False):
    install_language_space(app)
    app.state.language_space_installed = True
install_registration_routes(app)

# The original frontend depends on streaming chat, regeneration and message
# editing. Keep that compatibility layer explicit rather than hiding it inside
# database migrations.
app.add_middleware(ChatOverrideMiddleware)

# Activate the separate Melimi Telugu Lab workspace.
from app import lab_server  # noqa: E402,F401
