from __future__ import annotations

import json
from pathlib import Path

from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select

from app.auth import COOKIE_NAME
from app.database import Conversation, Message, SessionLocal, create_conversation, user_from_session
from app.server import app

LAB_PREFIX = "[Melimi Lab] "
ASSET_VERSION = "20260818-2"


def _headers(scope):
    return {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}


def _cookie_token(cookie_header: str) -> str:
    for part in cookie_header.split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key == COOKIE_NAME:
            return value
    return ""


def _is_lab_conversation(user_id: int, conversation_id: str) -> bool:
    with SessionLocal() as db:
        row = db.scalar(
            select(Conversation).where(
                (Conversation.id == conversation_id) & (Conversation.user_id == user_id)
            )
        )
        return bool(row and row.title.startswith(LAB_PREFIX))


def _lab_conversation(user_id: int, conversation_id: str | None, message: str) -> str:
    if conversation_id:
        if not _is_lab_conversation(user_id, conversation_id):
            raise ValueError("Conversation belongs to another workspace.")
        return conversation_id
    title = " ".join(message.strip().split())[:70] or "New lab session"
    return create_conversation(user_id, LAB_PREFIX + title, "melimi")


class LabWorkspaceMiddleware:
    """ASGI middleware that isolates the Melimi Lab workspace.

    Starlette instantiates middleware classes with the wrapped ASGI application.
    Keep that application on the instance instead of calling the global FastAPI
    object, which would both fail construction and risk recursive dispatch.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        method = scope.get("method", "").upper()
        headers = _headers(scope)

        if path == "/melimi-lab" and method == "GET":
            target = Path(__file__).resolve().parents[1] / "static" / "melimi-lab.html"
            html = target.read_text(encoding="utf-8")
            injection = f'<script defer src="/static/js/melimi-lab-workspace.js?v={ASSET_VERSION}"></script>'
            html = html.replace("</body>", injection + "</body>")
            await HTMLResponse(html, headers={"Cache-Control": "no-store"})(scope, receive, send)
            return
        if path == "/" and method == "GET":
            target = Path(__file__).resolve().parents[1] / "static" / "index.html"
            html = target.read_text(encoding="utf-8")
            injection = f'<script defer src="/static/js/main-workspace.js?v={ASSET_VERSION}"></script>'
            html = html.replace("</body>", injection + "</body>")
            await HTMLResponse(html, headers={"Cache-Control": "no-store"})(scope, receive, send)
            return

        if headers.get("x-teluai-workspace") != "lab":
            await self.app(scope, receive, send)
            return
        intercepted = (
            (path in {"/chat", "/chat/stream"} and method == "POST")
            or (path.startswith("/chat/") and method == "POST")
            or (path.startswith("/messages/") and method == "PATCH")
        )
        if not intercepted:
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
        user = user_from_session(_cookie_token(headers.get("cookie", "")))
        if user is None:
            async def replay_auth():
                return {"type": "http.request", "body": raw, "more_body": False}

            await self.app(scope, replay_auth, send)
            return

        try:
            body = json.loads(raw or b"{}")
            if path.startswith("/chat/") and path.endswith("/regenerate"):
                conversation_id = path[len("/chat/") : -len("/regenerate")].strip("/")
                if not _is_lab_conversation(user.id, conversation_id):
                    raise ValueError("Conversation belongs to another workspace.")
                body["conversation_id"] = conversation_id
                body["mode"] = "melimi"
            elif path.startswith("/messages/"):
                message_id = int(path.rsplit("/", 1)[1])
                with SessionLocal() as db:
                    row = db.get(Message, message_id)
                if not row or row.user_id != user.id or not _is_lab_conversation(user.id, row.conversation_id):
                    raise ValueError("Message belongs to another workspace.")
            else:
                body["conversation_id"] = _lab_conversation(
                    user.id,
                    body.get("conversation_id"),
                    str(body.get("message", "")),
                )
                body["mode"] = "melimi"
            rewritten = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        except Exception as exc:
            response = JSONResponse({"detail": str(exc)}, status_code=400)
            await response(scope, receive, send)
            return

        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": rewritten, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)


app.add_middleware(LabWorkspaceMiddleware)
