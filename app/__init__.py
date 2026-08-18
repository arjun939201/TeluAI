"""TeluAI application package."""

# Install presentation deduplication and chat-learning hooks before FastAPI
# routers import the affected helpers.
from app import language_space_dedupe as _language_space_dedupe  # noqa: F401
from app import chat_learning_runtime as _chat_learning_runtime  # noqa: F401

_chat_learning_runtime.install()

# The Melimi Lab page must be reachable at /melimi-lab. Register this at
# FastAPI application construction time so the route remains available even
# when app.main is deployed from a stale build or the route declaration is
# accidentally omitted from the main router module.
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


if not getattr(FastAPI, "_telua_melimi_lab_patch", False):
    _original_fastapi_init = FastAPI.__init__

    def _telua_fastapi_init(self, *args, **kwargs):
        _original_fastapi_init(self, *args, **kwargs)

        from app.workspace_guard import WorkspaceGuardMiddleware
        self.add_middleware(WorkspaceGuardMiddleware)

        def melimi_lab_page():
            target = Path(__file__).resolve().parent.parent / "static" / "melimi-lab.html"
            if not target.is_file():
                raise HTTPException(404, "Melimi Lab page not found.")
            return FileResponse(str(target))

        if not any(route.path == "/melimi-lab" for route in self.routes):
            self.add_api_route("/melimi-lab", melimi_lab_page, methods=["GET"], name="melimi_lab_page")

    FastAPI.__init__ = _telua_fastapi_init
    FastAPI._telua_melimi_lab_patch = True
