from app.conversation.state import ConversationState
from app.conversation.understanding import infer_intent
from app.prompts import MELIMI_SYSTEM, build_prompt


def test_enti_after_question_is_clarification():
    state = ConversationState(
        open_question="నీవు ఏమైనా ఆలోచిస్తున్నావా?"
    )
    result = infer_intent("enti", state)
    assert result["intent"] == "clarification_request"


def test_sare():
    assert infer_intent("sare", ConversationState())["intent"] == "agreement"


def test_cheppu():
    assert infer_intent("cheppu", ConversationState())["intent"] == "continue_current_topic"


def test_natural_telugu_what_question():
    result = infer_intent("ఏం జరుగుతుంది", ConversationState())
    assert result["intent"] == "what_question"


def test_melimi_prompt_is_conversation_first():
    assert "PRIMARY RULE — CONVERSATION BEFORE ANALYSIS" in MELIMI_SYSTEM
    assert "Never answer by explaining the user's own sentence" in MELIMI_SYSTEM
    prompt = build_prompt("melimi", conversation="previous turn", linguistics="internal hint", plan="internal plan")
    assert "INTERNAL LINGUISTIC HINTS" in prompt
    assert "INTERNAL RESPONSE PLAN" in prompt
    assert "DO NOT EXPOSE" in prompt
