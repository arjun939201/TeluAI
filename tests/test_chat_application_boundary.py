import asyncio

from app.chat.application import PreparedChatTurn, prepare_chat_turn


def test_chat_preparation_uses_single_application_boundary(monkeypatch):
    class User:
        id = 7

    async def fake_prepare_prompt(message, mode, history, user_id, response_length="normal"):
        class Decision:
            use_melimi = False
            language = "telugu"

        decision = Decision()
        decision.mode = mode
        return decision, "canonical prompt", {"intent": "conversation"}

    monkeypatch.setattr("app.chat.application.ensure_conversation", lambda *args: "conversation-1")
    monkeypatch.setattr("app.chat.application.context_for", lambda *args: ([{"role": "user", "content": "hi"}], ""))
    monkeypatch.setattr("app.chat.application.prepare_prompt", fake_prepare_prompt)

    turn = asyncio.run(prepare_chat_turn({"message": "hi", "mode": "auto"}, User()))

    assert isinstance(turn, PreparedChatTurn)
    assert turn.conversation_id == "conversation-1"
    assert turn.prompt == "canonical prompt"
    assert turn.metadata["intent"] == "conversation"
