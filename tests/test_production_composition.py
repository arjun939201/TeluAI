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


def test_main_workspace_script_defers_history_isolation_to_api():
    script = (ROOT / "static/js/main-workspace.js").read_text(encoding="utf-8")

    assert "Workspace separation is enforced by the API" in script
    assert "window.fetch" not in script
    assert "[Melimi Lab]" not in script
    assert "querySelector('.nav')" not in script
    assert "createElement('a')" not in script


def test_melimi_lab_is_a_real_canonical_route():
    server = (ROOT / "app/server.py").read_text(encoding="utf-8")
    lab = (ROOT / "static/melimi-lab.html").read_text(encoding="utf-8")

    assert '@app.get("/melimi-lab"' in server
    assert 'id="composer"' in lab
    assert 'id="chat"' in lab
    assert 'melimi-lab.js' in lab
    assert 'workspace-context.js' in lab
    assert "melimi-lab-workspace.js" not in server
