"""Production ASGI composition boundary for TeluAI.

Database migrations are schema-only. Runtime routes, chat behavior, workspace
boundaries and the Melimi Lab are composed explicitly here so importing or
migrating the database cannot mutate FastAPI application behavior.
"""
from app.main import app
from app.chat.middleware import ChatOverrideMiddleware
from app.chat_learning import install_chat_learning
from app.language_space import install_routes as install_language_space
from app.melimi.registration_routes import install_routes as install_registration_routes
from app.workspace_guard import WorkspaceGuardMiddleware


# Runtime application composition belongs at the ASGI boundary.
install_chat_learning()
if not getattr(app.state, "language_space_installed", False):
    install_language_space(app)
    app.state.language_space_installed = True
install_registration_routes(app)

# Middleware is registered in reverse nesting order. ChatOverride must be
# registered first so WorkspaceGuard becomes the outer boundary and can reject
# Lab-only commands before any chat command handling occurs.
app.add_middleware(ChatOverrideMiddleware)
app.add_middleware(WorkspaceGuardMiddleware)

# Activate the separate Melimi Telugu Lab workspace.
from app import lab_server  # noqa: E402,F401
