from app.conversation import build_state
from app.conversation.planner import plan_response_details


def test_possible_topic_shift_is_preserved_as_background_context():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ])
    plan = plan_response_details(
        {"intent": "how_question", "confidence": "medium"},
        {"dominant_signal": "question", "topic_relation": "possible_topic_shift"},
        state,
    )
    assert "possible topic shift" in plan["instruction"]
    assert "answer the current utterance" in plan["instruction"]


def test_continuation_keeps_established_topic_active():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ])
    plan = plan_response_details(
        {"intent": "continue_current_topic", "confidence": "medium"},
        {"dominant_signal": "statement", "topic_relation": "continuation"},
        state,
    )
    assert "established topic as active" in plan["instruction"]


def test_reference_signal_requires_prior_semantic_context():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ])
    plan = plan_response_details(
        {"intent": "contextual_statement", "confidence": "medium"},
        {"dominant_signal": "request", "reference_detected": True},
        state,
    )
    assert "reliable prior semantic context" in plan["instruction"]
