from __future__ import annotations

import json

from fastapi.responses import JSONResponse

from app.application.workspace_service import can_access_conversation, list_user_conversations, normalize_workspace
from app.auth import COOKIE_NAME
from app.database import user_from_session


def _workspace(scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == b"x-teluai-workspace":
            return normalize_workspace(value.decode("utf-8", "ignore"))
    return "main"


def _cookie_token(scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() != b"cookie":
            continue
        for part in value.decode("utf-8", "ignore").split(";"):
            name, sep, token = part.strip().partition("=")
            if sep and name == COOKIE_NAME:
                return token
    return ""


def _session_user(scope):
    try:
        return user_from_session(_cookie_token(scope))
    except Exception:
        return None


class WorkspaceGuardMiddleware:
    """Enforce workspace boundaries at the API boundary.

    This middleware owns transport concerns only. Workspace policy and data
    access live in the application service so the same rules can be reused by
    HTTP routes, background jobs, and future interfaces without duplicating
    authorization logic.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        workspace = _workspace(scope)

        if method == "GET" and path == "/conversations":
            user = _session_user(scope)
            if user is None:
                await self.app(scope, receive, send)
                return
            rows = list_user_conversations(user.id, workspace)
            visible = [
                {
                    "id": row.id,
                    "title": row.title,
                    "mode": row.mode,
                    "summary": row.summary,
                    "created_at": row.created_at.isoformat(),
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in rows
            ]
            await JSONResponse({"conversations": visible})(scope, receive, send)
            return

        if method in {"GET", "DELETE"} and path.startswith("/conversations/"):
            conversation_id = path[len("/conversations/"):].strip("/")
            user = _session_user(scope)
            if user is not None and conversation_id and not can_access_conversation(user.id, conversation_id, workspace):
                await JSONResponse(
                    {"detail": "Conversation belongs to another workspace."},
                    status_code=404,
                )(scope, receive, send)
                return

        if method != "POST" or not path.startswith("/chat/"):
            await self.app(scope, receive, send)
            return

        # Only the Lab transport needs payload normalization. Main chat keeps
        # the canonical command pipeline, including explicit /word teaching.
        if workspace != "lab":
            await self.app(scope, receive, send)
            return

        chunks = []
        while True:
            event = await receive()
            if event.get("type") == "http.disconnect":
                break
            if event.get("type") != "http.request":
                continue
            chunks.append(event.get("body", b""))
            if not event.get("more_body", False):
                break

        try:
            payload = json.loads(b"".join(chunks).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        payload["mode"] = "melimi"
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": raw, "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, replay, send)
