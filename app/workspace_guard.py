from __future__ import annotations

import json
from fastapi.responses import JSONResponse


def _workspace(scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == b"x-teluai-workspace":
            return "lab" if value.decode("utf-8", "ignore").strip().lower() == "lab" else "main"
    return "main"


class WorkspaceGuardMiddleware:
    """Keep Lab commands in the Lab even when the browser UI is bypassed."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method", "").upper() != "POST":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not (path == "/chat" or path == "/chat/stream" or path.startswith("/chat/")):
            await self.app(scope, receive, send)
            return

        chunks = []
        while True:
            event = await receive()
            if event.get("type") != "http.request":
                continue
            chunks.append(event.get("body", b""))
            if not event.get("more_body", False):
                break
        raw = b"".join(chunks)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        workspace = _workspace(scope)
        message = str(payload.get("message", "")).strip()
        if workspace == "main" and message.startswith("/"):
            if path == "/chat/stream" or path.startswith("/chat/"):
                body = (
                    'data: ' + json.dumps({"type": "error", "message": "Melimi Lab commands are available only in the Melimi Telugu Lab.", "code": "workspace_boundary"}, ensure_ascii=False)
                    + "\\n\\n"
                    + 'data: ' + json.dumps({"type": "done"}) + "\\n\\n"
                ).encode("utf-8")
                await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/event-stream")]})
                await send({"type": "http.response.body", "body": body, "more_body": False})
                return
            response = JSONResponse({"detail": {"message": "Melimi Lab commands are available only in the Melimi Telugu Lab.", "code": "workspace_boundary"}}, status_code=403)
            await response(scope, lambda: {"type": "http.request", "body": b"", "more_body": False}, send)
            return

        if workspace == "lab":
            payload["mode"] = "melimi"
            raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        sent = False
        async def replay():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": raw, "more_body": False}

        await self.app(scope, replay, send)
