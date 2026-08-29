from uuid import uuid4

from fastapi.testclient import TestClient

from app.teluai2_app import app


def test_chat_learns_user_suggestion_and_reuses_it(monkeypatch):
    seen_prompts = []

    async def fake_groq(prompt, history, message):
        seen_prompts.append(prompt)
        return {"answer": "సరే, కొనసాగిద్దాం.", "model": "test", "input_tokens": 1, "output_tokens": 2, "latency_ms": 1}

    monkeypatch.setattr("app.teluai2_app.call_groq_detailed", fake_groq)
    monkeypatch.setattr("app.teluai2_app.local_answer", lambda message, mode: None)

    username = "teluai2_" + uuid4().hex[:12]
    with TestClient(app) as client:
        auth = client.post("/auth/guest", json={"username": username, "password": "strong-pass-123"})
        assert auth.status_code == 200, auth.text

        taught = client.post("/chat", json={"message": "సంతోషం = అలరిక"})
        assert taught.status_code == 200, taught.text
        assert taught.json()["learned"]["value"] == "అలరిక"

        fresh = client.post("/chat", json={"message": "సంతోషం మేలిమిలో ఏమంటారు?"})
        assert fresh.status_code == 200, fresh.text
        assert seen_prompts
        assert "సంతోషం → అలరిక" in seen_prompts[-1]
