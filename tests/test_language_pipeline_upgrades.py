from app.chat_learning import parse_command
from app.conversation.state import ConversationState
from app.conversation.understanding import infer_intent
from app.prompts import build_prompt


def test_only_explicit_commands_are_learning_commands():
    assert parse_command("/word ద్వేషస్పదం = కంటుపాదు")[0] == "word"
    assert parse_command("/content ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి")[0] == "content"
    assert parse_command("సాధారణంగా ద్వేషస్పదం = కంటుపాదు") is None


def test_content_command_preserves_optional_meaning():
    kind, payload = parse_command("/content ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి (ప్రమాదకరమైన ప్రదేశాలు ఎన్నో మన ప్రపంచంలో ఉన్నాయి)")
    assert kind == "content"
    assert payload["content"].startswith("ముప్పుకాను")
    assert payload["meaning"].startswith("ప్రమాదకరమైన")


def test_short_followup_uses_context():
    state = ConversationState(open_question="నీవు ఏ పదం గురించి మాట్లాడుతున్నావు?")
    assert infer_intent("ఏం", state)["intent"] == "clarification_request"


def test_melimi_prompt_forbids_dictionary_style_echoing():
    prompt = build_prompt("melimi", conversation="previous assistant: నీకు ఏం కావాలి?")
    assert "PRIMARY RULE — CONVERSATION BEFORE ANALYSIS" in prompt
    assert "Never answer by explaining the user's own sentence" in prompt
    assert "Do not turn ordinary conversation into language analysis" in prompt
