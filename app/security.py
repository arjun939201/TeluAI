from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings


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
        ("/auth/forgot-password", 5, 300),
        ("/auth/verify-reset-code", 10, 300),
        ("/auth/reset-password", 6, 300),
        ("/melimi/content/upload", 10, 300),
    )

    async def dispatch(self, request, call_next):
        if settings.testing:
            return await call_next(request)
        now = time.monotonic()
        key_base = client_identifier(request)
        for prefix, limit, window in self.RULES:
            if request.url.path == prefix:
                key = (prefix, key_base)
                bucket = self._buckets[key]
                while bucket and now - bucket[0] >= window:
                    bucket.popleft()
                if len(bucket) >= limit:
                    from starlette.responses import JSONResponse
                    return JSONResponse({"detail": "Too many requests. Please try again later."}, status_code=429)
                bucket.append(now)
                break
        return await call_next(request)

    def __init__(self, app):
        super().__init__(app)
        self._buckets = defaultdict(deque)
