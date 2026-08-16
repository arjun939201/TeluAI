import os

os.environ.pop("RENDER", None)
os.environ["CACHE_ENABLED"] = "false"

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_guest_lifecycle():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["service"] == "TeluAI"

        guest = client.post("/auth/guest", json={"username": "smoke_guest", "password": "strong-pass-123"})
        assert guest.status_code == 200, guest.text
        assert guest.json()["role"] == "guest"

        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] is None

        credentials = client.put("/me/credentials", json={
            "current_password": "strong-pass-123",
            "username": "smoke_guest_2",
        })
        assert credentials.status_code == 200, credentials.text
        assert credentials.json()["username"] == "smoke_guest_2"

        client.post("/auth/logout")
        login = client.post("/auth/login", json={
            "identifier": "smoke_guest_2",
            "password": "strong-pass-123",
        })
        assert login.status_code == 200, login.text
        assert login.json()["role"] == "guest"


def test_conversation_uuid_route():
    with TestClient(app) as client:
        guest = client.post("/auth/guest", json={"username": "conversation_guest", "password": "strong-pass-123"})
        assert guest.status_code == 200, guest.text

        from app import database as db
        user = db.user_from_session(client.cookies.get("teluai_session"))
        conversation_id = db.create_conversation(user.id, "Smoke test", "melimi")

        detail = client.get(f"/conversations/{conversation_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["conversation_id"] == conversation_id

        deleted = client.delete(f"/conversations/{conversation_id}")
        assert deleted.status_code == 200, deleted.text
