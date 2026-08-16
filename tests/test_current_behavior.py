from app.conversation.state import ConversationState
from app.conversation.understanding import infer_intent


def test_natural_telugu_what_question_is_detected():
    result = infer_intent("ఏం జరుగుతుంది", ConversationState())
    assert result["intent"] == "what_question"


def test_short_what_after_question_is_clarification():
    state = ConversationState(open_question="నీవు ఏమైనా ఆలోచిస్తున్నావా?")
    result = infer_intent("ఏం", state)
    assert result["intent"] == "clarification_request"
