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


def test_main_workspace_is_single_telugu_chat_surface():
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/main-workspace.js").read_text(encoding="utf-8")

    assert 'id="composer"' in html
    assert 'id="chat"' in html
    assert 'id="input"' in html
    assert 'id="send"' in html
    assert 'href="/melimi-lab"' not in html
    assert 'Melimi Telugu Lab' not in html
    assert 'Write a Python function' not in html
    assert 'What is Python and why is it useful?' not in html
    assert "Workspace separation is enforced by the API" not in script
    assert "[Melimi Lab]" not in script


def test_no_lab_route_is_exposed_by_the_application():
    server = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert '@app.get("/melimi-lab"' not in server
    assert 'Melimi Telugu Lab' not in server
