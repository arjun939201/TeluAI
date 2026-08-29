from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_entrypoints_use_canonical_server():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert '"app.server:app"' in dockerfile
    assert "uvicorn app.server:app" in render
    assert "app.main:app" not in dockerfile
    assert "app.lab_server:app" not in render


def test_frontend_does_not_replace_native_streaming_transport():
    engine = (ROOT / "static/js/teluai-engine.js").read_text(encoding="utf-8")

    assert "window.fetch" not in engine
    assert "'/chat'" not in engine
    assert "ReadableStream" not in engine
    assert "/health" in engine


def test_main_workspace_script_only_filters_lab_history():
    script = (ROOT / "static/js/main-workspace.js").read_text(encoding="utf-8")

    assert "[Melimi Lab]" in script
    assert "querySelector('.nav')" not in script
    assert "createElement('a')" not in script
