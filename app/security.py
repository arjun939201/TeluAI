"""Application security helpers.

The limiter is intentionally dependency-free and process-local. It protects the
single-process Render deployment and development environments without adding a
Redis requirement. If TeluAI is later scaled horizontally, move the same
contract to a shared store such as Redis.
"""
from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry = max(1, int(events[0] + window_seconds - now + 0.999))
                return False, retry
            events.append(now)
            if len(self._events) > 10_000:
                self._prune_locked(cutoff)
        return True, 0

    def _prune_locked(self, cutoff: float) -> None:
        for key in list(self._events):
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                self._events.pop(key, None)


RATE_LIMITER = SlidingWindowLimiter()


def client_identifier(request: Request) -> str:
    # Forwarded headers are only trusted when the deployment explicitly says
    # it is behind a trusted proxy. Otherwise use the socket peer address.
    if request.app.state.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded[:128]
    return (request.client.host if request.client else "unknown")[:128]


def session_fingerprint(request: Request) -> str:
    token = request.cookies.get("teluai_session", "")
    if not token:
        return "anonymous"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:20]


class RateLimitMiddleware(BaseHTTPMiddleware):
    RULES = (
        ("/chat", 30, 60),
        ("/auth/login", 10, 60),
        ("/auth/register", 6, 300),
        ("/auth/guest", 6, 300),
        ("/auth/forgot-password", 5, 300),
        ("/auth/verify-reset-code", 10, 300),
        ("/auth/reset-password", 6, 300),
        ("/melimi/content/upload", 10, 300),
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        rule = next((item for item in self.RULES if path == item[0] or path.startswith(item[0] + "/")), None)
        if rule is not None:
            route, limit, window = rule
            identity = client_identifier(request)
            if route == "/chat":
                identity = f"{identity}:{session_fingerprint(request)}"
            allowed, retry_after = RATE_LIMITER.check(f"{route}:{identity}", limit, window)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again shortly."},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.app.state.secure_transport:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
