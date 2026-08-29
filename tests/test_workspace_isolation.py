from fastapi.testclient import TestClient

from app.server import app


def _guest(client, username):
    response = client.post(
        "/auth/guest",
        json={"username": username, "password": "strong-pass-123"},
    )
    assert response.status_code == 200, response.text


def test_conversation_list_is_server_side_workspace_scoped():
    with TestClient(app) as client:
        _guest(client, "workspace_scope_guest")

        # Use a deterministic native Melimi request: this test verifies
        # persistence/workspace boundaries, not external provider availability.
        main = client.post("/chat", json={"message": "సినిమా", "mode": "melimi"})
        assert main.status_code == 200, main.text
        main_id = main.json()["conversation_id"]

        lab = client.post(
            "/chat/stream",
            headers={"X-TeluAI-Workspace": "lab"},
            json={"message": "lab conversation", "mode": "standard"},
        )
        assert lab.status_code == 200, lab.text

        main_rows = client.get("/conversations").json()["conversations"]
        lab_rows = client.get(
            "/conversations", headers={"X-TeluAI-Workspace": "lab"}
        ).json()["conversations"]

        assert any(row["id"] == main_id for row in main_rows)
        assert all(not row["title"].startswith("[Melimi Lab] ") for row in main_rows)
        assert lab_rows
        assert all(row["title"].startswith("[Melimi Lab] ") for row in lab_rows)


def test_conversation_id_cannot_cross_workspace_boundary():
    with TestClient(app) as client:
        _guest(client, "workspace_boundary_guest")
        lab = client.post(
            "/chat/stream",
            headers={"X-TeluAI-Workspace": "lab"},
            json={"message": "isolated lab conversation", "mode": "standard"},
        )
        assert lab.status_code == 200, lab.text
        rows = client.get(
            "/conversations", headers={"X-TeluAI-Workspace": "lab"}
        ).json()["conversations"]
        assert rows
        lab_id = rows[0]["id"]

        detail = client.get(f"/conversations/{lab_id}")
        assert detail.status_code == 404

        delete = client.delete(f"/conversations/{lab_id}")
        assert delete.status_code == 404

        lab_detail = client.get(
            f"/conversations/{lab_id}",
            headers={"X-TeluAI-Workspace": "lab"},
        )
        assert lab_detail.status_code == 200
