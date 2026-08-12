from app.conversation.state import ConversationState
from app.conversation.understanding import understand_user_turn


def test_enti_is_contextual_clarification():
    state = ConversationState()
    state.add_turn("assistant", "నీవు ఏమైనా ఆలోచిస్తున్నావా?")
    state.open_question = state.recent_turns[-1].content

    result = understand_user_turn("enti", state)

    assert result["intent"] == "clarification_request"


def test_sare_is_agreement():
    state = ConversationState()
    result = understand_user_turn("sare", state)
    assert result["intent"] == "agreement"


def test_cheppu_requests_continuation():
    state = ConversationState()
    result = understand_user_turn("cheppu", state)
    assert result["intent"] == "continue_request"
