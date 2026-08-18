from fastapi.testclient import TestClient

from app.main import app
from app import database as db


def test_explicit_word_command_is_master_and_normal_mapping_is_ignored():
    with TestClient(app) as client:
        guest = client.post("/auth/guest", json={"username": "command_guest", "password": "strong-pass-123"})
        assert guest.status_code == 200, guest.text

        normal = client.post("/chat", json={"message": "ద్వేషస్పదం = కంటుపాదు", "mode": "melimi"})
        # A normal mapping is not a language command. In CI no Groq token is
        # configured, so the request may legitimately fail with the provider
        # configuration status; the important invariant is that it must not
        # silently promote the mapping into MASTER language data.
        assert normal.status_code in {200, 502, 503}, normal.text
        with db.SessionLocal() as session:
            assert session.scalar(db.select(db.MelimiRoot).where(db.MelimiRoot.standard_root == "ద్వేషస్పదం")) is None

        command = client.post("/chat", json={"message": "/word ద్వేషస్పదం = కంటుపాదు", "mode": "melimi"})
        assert command.status_code == 200, command.text
        assert "MASTER" in command.json()["reply"]
        with db.SessionLocal() as session:
            row = session.scalar(db.select(db.MelimiRoot).where(db.MelimiRoot.standard_root == "ద్వేషస్పదం"))
            assert row is not None
            assert row.melimi_root == "కంటుపాదు"
            assert row.status == "MASTER"


def test_explicit_content_command_is_master():
    with TestClient(app) as client:
        guest = client.post("/auth/guest", json={"username": "content_command_guest", "password": "strong-pass-123"})
        assert guest.status_code == 200, guest.text
        text = "ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి"
        response = client.post("/chat", json={"message": f"/content {text} (ప్రమాదకరమైన ప్రదేశాలు ఎన్నో మన ప్రపంచంలో ఉన్నాయి)", "mode": "melimi"})
        assert response.status_code == 200, response.text
        with db.SessionLocal() as session:
            row = session.scalar(db.select(db.KnowledgeEntry).where(db.KnowledgeEntry.kind == "CONTENT", db.KnowledgeEntry.value == text))
            assert row is not None
            assert row.status == "MASTER"
