"""Production ASGI composition boundary for TeluAI.

The ASGI boundary composes the application. Domain and application policy stay
out of transport middleware so every interface can reuse the same rules.
"""
from pathlib import Path

from fastapi.responses import HTMLResponse

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


@app.get("/melimi-lab", response_class=HTMLResponse)
def melimi_lab_page() -> HTMLResponse:
    """Serve the real Lab application from the canonical ASGI app.

    The Lab page must not depend on importing another module that imports this
    module back again. Keeping the presentation route here makes production
    composition deterministic and guarantees /melimi-lab exists in Render.
    """
    target = Path(__file__).resolve().parents[1] / "static" / "melimi-lab.html"
    if not target.is_file():
        return HTMLResponse("Melimi Lab frontend not found.", status_code=404)
    html = target.read_text(encoding="utf-8")
    # The Lab document already loads melimi-lab.js. Only add a cache-busting
    # marker to the document itself; do not inject a nonexistent script.
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


# Starlette applies middleware in reverse registration order. The workspace
# guard must sit outside chat overrides so transport boundaries are enforced
# before any downstream chat handling.
app.add_middleware(ChatOverrideMiddleware)
app.add_middleware(WorkspaceGuardMiddleware)
