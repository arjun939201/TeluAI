"""Compatibility entrypoint and TEX-L route registration."""

from app.teluai2_app import app
from app.texl_routes import router as texl_router

app.include_router(texl_router)

__all__ = ["app"]
