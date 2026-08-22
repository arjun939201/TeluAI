import asyncio

from app.chat.application import PreparedChatTurn
from app.chat import middleware


def _turn():
    class Decision:
        mode = "auto"
        use_melimi = False
        language = "telugu"

    return PreparedChatTurn(
        message="hello",
        conversation_id="conversation-1",
        history=[],
        decision=Decision(),
        prompt="canonical prompt",
        metadata={"intent": "conversation"},
    )


def test_middleware_preparation_delegates_to_application_boundary(monkeypatch):
    calls = []

    async def fake_prepare(data, user):
        calls.append((data, user))
        return _turn()

    monkeypatch.setattr(middleware, "prepare_chat_turn", fake_prepare)

    class User:
        id = 7

    user = User()
    result = asyncio.run(middleware._prepare({"message": "hello"}, user))

    assert result.prompt == "canonical prompt"
    assert calls == [({"message": "hello"}, user)]


def test_transport_uses_async_canonical_preparation_shim():
    assert hasattr(middleware.ChatOverrideMiddleware, "__call__")
    assert asyncio.iscoroutinefunction(middleware._prepare)
