"""Canonical production ASGI entrypoint for TeluAI.

The production boundary also installs chat-learning scope enforcement so
trusted owner/admin conversations can teach shared Melimi knowledge while
ordinary user contributions remain private to their account.
"""
from __future__ import annotations

import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.main import app
from app.auth import COOKIE_NAME
from app.database import user_from_session
from app.learning_scope import exact_mapping, record_chat_learning, search_learning, reset_request_user, set_request_user


class ScopedLearningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        raw_session = request.cookies.get(COOKIE_NAME)
        user = user_from_session(raw_session) if raw_session else None
        tokens = set_request_user(getattr(user, "id", None), getattr(user, "role", "user"))
        try:
            response = await call_next(request)
            if request.method == "POST" and request.url.path == "/chat" and user is not None:
                try:
                    payload = json.loads((await request.body()).decode("utf-8"))
                    message = str(payload.get("message", "")).strip() if isinstance(payload, dict) else ""
                    if message:
                        record_chat_learning(user.id, user.role, message)
                except Exception:
                    # Learning is non-critical. Never turn a successful chat into
                    # an error because persistence of advisory learning failed.
                    pass
            return response
        finally:
            reset_request_user(tokens)


def _scoped_local_answer(message: str, mode: str):
    """Prefer scoped chat learning for direct Melimi lookups."""
    if mode == "melimi":
        user_id = __import__("app.learning_scope", fromlist=["CURRENT_USER_ID"]).CURRENT_USER_ID.get()
        if user_id is not None:
            from app.local_answer import _extract_lookup_word
            word = _extract_lookup_word(message)
            if word:
                learned = exact_mapping(word, user_id)
                if learned:
                    return learned
    return _original_local_answer(message, mode)


_original_local_answer = app.main.local_answer
app.main.local_answer = _scoped_local_answer
app.add_middleware(ScopedLearningMiddleware)

__all__ = ["app"]
