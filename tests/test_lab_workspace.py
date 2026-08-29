import os

os.environ.pop("RENDER", None)
os.environ["CACHE_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.server import app


def _guest(client, username):
    response = client.post(
        "/auth/guest",
        json={"username": username, "password": "strong-pass-123"},
    )
    assert response.status_code == 200, response.text


def test_melimi_lab_page_is_served_by_canonical_route():
    with TestClient(app) as client:
        response = client.get("/melimi-lab")
        assert response.status_code == 200, response.text
        assert "Melimi Telugu Lab" in response.text
        assert 'id="composer"' in response.text
        assert 'id="chat"' in response.text
        assert 'data-page="melimi-lab"' in response.text
        # The document owns its real assets; the server must not inject a
        # competing/nonexistent workspace bundle.
        assert '/static/js/melimi-lab.js' in response.text
        assert '/static/js/workspace-context.js' in response.text
        assert 'melimi-lab-workspace.js?v=' not in response.text


def test_commands_are_blocked_outside_lab():
    with TestClient(app) as client:
        _guest(client, "workspace_main_guest")
        response = client.post(
            "/chat/stream",
            json={"message": "/word hello = నమస్కారం", "mode": "melimi"},
        )
        assert response.status_code == 200
        assert "workspace_boundary" in response.text
        assert "Melimi Lab commands are available only in the Melimi Telugu Lab." in response.text


def test_lab_command_uses_lab_workspace_and_persists():
    with TestClient(app) as client:
        _guest(client, "workspace_lab_guest")
        response = client.post(
            "/chat/stream",
            headers={"X-TeluAI-Workspace": "lab"},
            json={"message": "/word hello = నమస్కారం", "mode": "standard"},
        )
        assert response.status_code == 200, response.text
        assert "language_command" in response.text
        assert "PENDING" in response.text

        conversations = client.get(
            "/conversations",
            headers={"X-TeluAI-Workspace": "lab"},
        )
        assert conversations.status_code == 200, conversations.text
        rows = conversations.json()["conversations"]
        assert rows
        assert all(str(row["title"]).startswith("[Melimi Lab] ") for row in rows)
