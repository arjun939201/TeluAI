from app.conversation import build_state, understanding_context


def test_state_uses_latest_substantive_user_turn_as_topic_anchor():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
        {"role": "user", "content": "చెప్పు"},
    ])
    assert state.topic == "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"


def test_short_continuation_keeps_established_topic():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ])
    context = understanding_context("చెప్పు", state)
    assert "current topic anchor: ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?" in context
    assert "topic relation: continuation" in context


def test_unrelated_substantive_turn_is_only_a_possible_shift():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
    ])
    context = understanding_context("ఈ రోజు వాతావరణం ఎలా ఉంది?", state)
    assert "topic relation: possible_topic_shift" in context
