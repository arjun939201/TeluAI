from app.conversation import build_state


def test_multi_turn_memory_keeps_bounded_recent_window():
    history = [{"role": "user", "content": f"message {i}"} for i in range(15)]
    state = build_state(history)
    assert len(state.recent) == state.memory_turns
    assert state.last_user == "message 14"
    assert state.recent[0].content == "message 5"


def test_multi_turn_memory_retains_semantic_facts_when_reconstructing_state():
    state = build_state([
        {"role": "user", "content": "ధన్యవాదం మేలిమి తెలుగులో ఏమంటారు?"},
        {"role": "assistant", "content": "నెనరు అంటారు."},
        {"role": "user", "content": "దాన్ని వాడి చెప్పు."},
    ])
    assert state.semantic_facts is not None


def test_failed_semantic_enrichment_does_not_break_history_reconstruction():
    state = build_state([
        {"role": "user", "content": "plain conversational text"},
        {"role": "assistant", "content": "సరే"},
    ])
    assert state.last_user == "plain conversational text"
    assert state.last_assistant == "సరే"
