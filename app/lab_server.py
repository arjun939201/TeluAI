"""Melimi Lab presentation routes.

Workspace authorization and chat transport belong to ``WorkspaceGuardMiddleware``
and the application layer. This module only serves the Lab document shell.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.responses import HTMLResponse

from app.server import app

ASSET_VERSION = "20260829-2"


@app.get("/melimi-lab", response_class=HTMLResponse)
def melimi_lab_page() -> HTMLResponse:
    target = Path(__file__).resolve().parents[1] / "static" / "melimi-lab.html"
    if not target.exists():
        return HTMLResponse("Melimi Lab frontend not found.", status_code=404)
    html = target.read_text(encoding="utf-8")
    injection = f'<script defer src="/static/js/melimi-lab-workspace.js?v={ASSET_VERSION}"></script>'
    html = html.replace("</body>", injection + "</body>")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
