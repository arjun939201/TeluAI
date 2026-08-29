from pathlib import Path

from app.teluai2_app import STATIC_DIR, app


def test_static_assets_are_mounted():
    assert STATIC_DIR.is_dir()
    assert (STATIC_DIR / "index.html").is_file()
    assert (STATIC_DIR / "teluai2.css").is_file()
    assert any(route.path.startswith("/static") for route in app.routes)
