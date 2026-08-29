"""Compatibility entrypoint.

TeluAI now exposes one product surface: Telugu conversation with personal
language learning. Keep this module as a stable import target for deployments
or older tooling that still imports app.main.
"""

from app.teluai2_app import app

__all__ = ["app"]
