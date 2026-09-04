from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SlidingWindowLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = Lock()

    def check(self, key, limit, window_seconds):
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                return False, max(1, int(events[0] + window_seconds - now + 0.999))

            events.append(now)
            if len(self._events) > 10000:
                self._prune_locked(cutoff)

        return True, 0

    def _prune_locked(self, cutoff):
        for key in list(self._events):
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                self._events.pop(key, None)


RATE_LIMITER = SlidingWindowLimiter()


def client_identifier(request: Request):
    if request.app.state.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded[:128]
    return (request.client.host if request.client else "unknown")[:128]


def session_fingerprint(request: Request):
    token = request.cookies.get("teluai_session", "")
    if token:
        return hashlib.sha256(token.encode()).hexdigest()[:20]
    return "anonymous"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit sensitive endpoints in production.

    Tests explicitly run with TELUAI_TESTING=true so their many independent
    users do not share a real-world IP quota. Production retains the same
    limits and enforcement path.
    """

    RULES = (
        ("/auth/login", 10, 60),
        ("/auth/register", 6, 300),
        ("/auth/guest", 6, 300),
        ("/auth/forgot-password", 5, 300),
        ("/auth/verify-reset-code", 10, 300),
        ("/auth/reset-password", 6, 300),
        ("/melimi/content/upload", 10, 300),
    )

    async def dispatch(self, request, call_next):
        if settings.testing:
            return await call_next(request)

        path = request.url.path
        rule = next((x for x in self.RULES if path == x[0] or path.startswith(x[0] + "/")), None)
        if rule:
            route, limit, window = rule
            allowed, retry = RATE_LIMITER.check(f"{route}:{client_identifier(request)}", limit, window)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again shortly."},
                    headers={"Retry-After": str(retry)},
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://teluai.onrender.com https://teluai.github.io; "
            "frame-ancestors 'self' https://teluai.github.io; "
            "base-uri 'self'; form-action 'self'; object-src 'none'",
        )
        if request.app.state.secure_transport:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
