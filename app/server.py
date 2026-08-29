"""Production ASGI composition boundary for TeluAI.

The ASGI boundary composes the application. Domain and application policy stay
out of transport middleware so every interface can reuse the same rules.
"""
from app.main import app
from app.chat.middleware import ChatOverrideMiddleware
from app.chat_learning import install_chat_learning
from app.language_space import install_routes as install_language_space
from app.melimi.registration_routes import install_routes as install_registration_routes
from app.workspace_guard import WorkspaceGuardMiddleware


install_chat_learning()
if not getattr(app.state, "language_space_installed", False):
    install_language_space(app)
    app.state.language_space_installed = True
install_registration_routes(app)

# Starlette applies middleware in reverse registration order. The workspace
# guard must sit outside chat overrides so transport boundaries are enforced
# before any downstream chat handling.
app.add_middleware(ChatOverrideMiddleware)
app.add_middleware(WorkspaceGuardMiddleware)

# Import for side-effect registration of the Lab HTTP presentation layer.
from app import lab_server  # noqa: E402,F401
