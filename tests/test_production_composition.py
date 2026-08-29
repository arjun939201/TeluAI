from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_entrypoints_use_canonical_server():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert '"app.server:app"' in dockerfile
    assert "uvicorn app.server:app" in render
    assert "app.main:app" not in dockerfile
    assert "app.lab_server:app" not in render


def test_frontend_does_not_replace_native_chat_transport():
    engine = (ROOT / "static/js/teluai-engine.js").read_text(encoding="utf-8")

    assert "window.fetch" not in engine
    assert "'/chat'" not in engine
    assert "ReadableStream" not in engine
    assert "/health" in engine


def test_single_chat_frontend_has_no_workspace_compatibility_surface():
    index = (ROOT / "static/index.html").read_text(encoding="utf-8")
    assert "/melimi-lab" not in index
    assert "Melimi Telugu Lab" not in index
    assert "workspace" not in index.lower()
    assert not (ROOT / "static/js/main-workspace.js").exists()


def test_production_server_is_the_single_fastapi_boundary():
    server = (ROOT / "app/server.py").read_text(encoding="utf-8")
    assert "from app.teluai2_app import app" in server
    assert "WorkspaceGuardMiddleware" not in server
    assert "workspace_guard" not in server
