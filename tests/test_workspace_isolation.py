from fastapi.testclient import TestClient

from app.server import app


def _guest(client, username):
    response = client.post(
        "/auth/guest",
        json={"username": username, "password": "strong-pass-123"},
    )
    assert response.status_code == 200, response.text


def test_conversation_list_is_server_side_user_scoped():
    with TestClient(app) as client:
        _guest(client, "conversation_scope_guest")
        response = client.post("/chat", json={"message": "సినిమా", "mode": "melimi"})
        assert response.status_code == 200, response.text
        conversation_id = response.json()["conversation_id"]

        rows = client.get("/conversations")
        assert rows.status_code == 200, rows.text
        conversations = rows.json()["conversations"]
        assert any(row["id"] == conversation_id for row in conversations)
        assert all(not row["title"].startswith("[Melimi Lab] ") for row in conversations)


def test_conversation_id_cannot_cross_user_boundary():
    with TestClient(app) as client:
        _guest(client, "conversation_owner_guest")
        created = client.post("/chat", json={"message": "సినిమా", "mode": "melimi"})
        assert created.status_code == 200, created.text
        conversation_id = created.json()["conversation_id"]

        client.post("/auth/logout")
        _guest(client, "conversation_other_guest")

        rows = client.get("/conversations")
        assert rows.status_code == 200, rows.text
        assert all(row["id"] != conversation_id for row in rows.json()["conversations"])

        detail = client.get(f"/conversations/{conversation_id}")
        assert detail.status_code == 404

        delete = client.delete(f"/conversations/{conversation_id}")
        assert delete.status_code == 404
