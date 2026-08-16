import asyncio

from app.security import SlidingWindowLimiter


def test_sliding_window_limiter_blocks_after_limit():
    limiter = SlidingWindowLimiter()
    assert limiter.check("user", 2, 60)[0] is True
    assert limiter.check("user", 2, 60)[0] is True
    allowed, retry = limiter.check("user", 2, 60)
    assert allowed is False
    assert retry >= 1


def test_rate_limits_are_isolated_by_key():
    limiter = SlidingWindowLimiter()
    assert limiter.check("a", 1, 60)[0] is True
    assert limiter.check("b", 1, 60)[0] is True
    assert limiter.check("a", 1, 60)[0] is False


def test_security_middleware_module_imports_without_network_dependencies():
    # Importing the security layer must not initialize external services.
    import app.security as security
    assert security.RATE_LIMITER is not None
