
from app.conversation import TurnState, infer_intent


def test_enti_after_question_is_clarification():
    state = TurnState(last_assistant="నీవు ఏమైనా ఆలోచిస్తున్నావా?", open_question="నీవు ఏమైనా ఆలోచిస్తున్నావా?")
    assert infer_intent("enti", state) == "clarification_request"


def test_sare_is_agreement():
    assert infer_intent("sare", TurnState()) == "agreement"


def test_cheppu_continues_current_topic():
    assert infer_intent("cheppu", TurnState()) == "continue_current_topic"
