from __future__ import annotations

import json

from fastapi.responses import JSONResponse

from app.auth import COOKIE_NAME
from app.database import Conversation, Message, SessionLocal, user_from_session

LAB_PREFIX = "[Melimi Lab] "


def _workspace(scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == b"x-teluai-workspace":
            return "lab" if value.decode("utf-8", "ignore").strip().lower() == "lab" else "main"
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


def _is_lab_conversation(row: Conversation | None) -> bool:
    return bool(row and str(row.title or "").startswith(LAB_PREFIX))


def _conversation_in_workspace(user_id: int, conversation_id: str, workspace: str) -> bool:
    with SessionLocal() as db:
        row = db.scalar(
            __import__("sqlalchemy").select(Conversation).where(
                (Conversation.id == conversation_id) & (Conversation.user_id == user_id)
            )
        )
    return bool(row and (_is_lab_conversation(row) == (workspace == "lab")))


def _message_is_command(payload: dict) -> bool:
    message = str(payload.get("message", "")).strip()
    if message.startswith("/"):
        return True
    message_id = payload.get("message_id")
    if message_id is None:
        return False
    try:
        with SessionLocal() as db:
            row = db.get(Message, int(message_id))
        return bool(row and str(row.content or "").strip().startswith("/"))
    except (TypeError, ValueError):
        return False


class WorkspaceGuardMiddleware:
    """Enforce workspace boundaries at the API boundary, not in the UI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        workspace = _workspace(scope)

        # Conversation history is workspace-scoped on the server. This removes
        # the need for the frontend to fetch everything and hide the wrong rows.
        if method == "GET" and path == "/conversations":
            user = _session_user(scope)
            if user is None:
                await self.app(scope, receive, send)
                return
            with SessionLocal() as db:
                rows = db.scalars(
                    __import__("sqlalchemy").select(Conversation)
                    .where(Conversation.user_id == user.id)
                    .order_by(Conversation.updated_at.desc())
                ).all()
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
                if _is_lab_conversation(row) == (workspace == "lab")
            ]
            response = JSONResponse({"conversations": visible})
            await response(scope, receive, send)
            return

        # Prevent a conversation ID from being used to cross the main/Lab
        # boundary even when the caller knows the UUID.
        if method in {"GET", "DELETE"} and path.startswith("/conversations/"):
            conversation_id = path[len("/conversations/"):].strip("/")
            user = _session_user(scope)
            if user is not None and conversation_id:
                if not _conversation_in_workspace(user.id, conversation_id, workspace):
                    response = JSONResponse({"detail": "Conversation belongs to another workspace."}, status_code=404)
                    await response(scope, receive, send)
                    return

        if method != "POST" or not (path == "/chat/stream" or path.startswith("/chat/")):
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
        raw = b"".join(chunks)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        if workspace == "main" and _message_is_command(payload):
            body = (
                "data: " + json.dumps({
                    "type": "error",
                    "message": "Melimi Lab commands are available only in the Melimi Telugu Lab.",
                    "code": "workspace_boundary",
                }, ensure_ascii=False)
                + "\n\n"
                + "data: " + json.dumps({"type": "done"})
                + "\n\n"
            ).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream")],
            })
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        if workspace == "lab":
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
