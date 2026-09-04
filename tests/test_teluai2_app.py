from uuid import uuid4

from fastapi.testclient import TestClient

from app.teluai2_app import app


def test_chat_learns_user_suggestion_and_reuses_it(monkeypatch):
    seen_prompts = []

    async def fake_groq(prompt, history, message):
        seen_prompts.append(prompt)
        return {"answer": "సరే, కొనసాగిద్దాం.", "model": "test", "input_tokens": 1, "output_tokens": 2, "latency_ms": 1}

    monkeypatch.setattr("app.teluai2_app.call_groq_detailed", fake_groq)

    suffix = uuid4().hex[:12]
    username = "teluai2_" + suffix
    email = "teluai2_" + suffix + "@example.com"
    with TestClient(app) as client:
        auth = client.post("/auth/register", json={"username": username, "email": email, "password": "strong-pass-123"})
        assert auth.status_code == 200, auth.text
        assert auth.json()["role"] != "guest"

        guest = client.post("/auth/guest", json={"username": "should_not_exist", "password": "strong-pass-123"})
        assert guest.status_code == 404

        taught = client.post("/chat", json={"message": "సంతోషం = అలరిక"})
        assert taught.status_code == 200, taught.text
        learned = taught.json()["learned"]
        assert any(item["key"] == "సంతోషం" and item["value"] == "అలరిక" for item in learned)

        fresh = client.post("/chat", json={"message": "సంతోషం మేలిమిలో ఏమంటారు?"})
        assert fresh.status_code == 200, fresh.text
        assert seen_prompts
        assert "సంతోషం → అలరిక" in seen_prompts[-1]
