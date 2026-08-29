"""Shared test-process configuration.

The production rate limiter is intentionally disabled for the test process so
hundreds of integration requests do not compete for a real client IP quota.
Production never sets TELUAI_TESTING.
"""

import os

os.environ.setdefault("TELUAI_TESTING", "true")
os.environ.setdefault("CACHE_ENABLED", "false")
