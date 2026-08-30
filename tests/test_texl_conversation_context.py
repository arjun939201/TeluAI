from app.conversation import build_state, understanding_context
from app.teluai2_app import _build_prompt


def test_conversation_state_retains_previous_turns():
    history = [
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ]
    state = build_state(history)
    assert state.last_user == "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"
    assert state.last_assistant == "నెనరు అంటారు."


def test_short_followup_is_contextual():
    history = [{"role": "assistant", "content": "ఇంకా ఏమైనా కావాలా?"}]
    context = understanding_context("చెప్పు", build_state(history))
    assert "continue_current_topic" in context
    assert "ఇంకా ఏమైనా కావాలా?" in context


def test_chat_prompt_includes_conversation_understanding():
    prompt = _build_prompt(
        "దాన్ని ఒక వాక్యంలో వాడు.",
        [
            {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
            {"role": "assistant", "content": "నెనరు అంటారు."},
        ],
        1,
        "normal",
    )
    assert "CONVERSATION UNDERSTANDING:" in prompt
    assert "దాన్ని ఒక వాక్యంలో వాడు." in prompt
    assert "నెనరు అంటారు." in prompt
