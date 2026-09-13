"""Compatibility entrypoint and route registration."""

from app.teluai2_app import app
from app.moderation_routes import router as moderation_router
from app.texl_routes import router as texl_router

app.include_router(texl_router)
app.include_router(moderation_router)

__all__ = ["app"]
