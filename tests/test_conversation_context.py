from app.conversation import build_state
from app.conversation.context import context_budget, select_context


def test_context_selection_keeps_latest_turns_within_budget():
    state = build_state([
        {"role": "user", "content": "old " + "x" * 100},
        {"role": "assistant", "content": "middle " + "y" * 100},
        {"role": "user", "content": "latest"},
    ])
    turns = select_context(state, max_chars=120)
    assert turns
    assert turns[-1].content == "latest"
    assert sum(len(turn.content) for turn in turns) <= 120


def test_context_budget_is_non_mutating_and_reports_bounds():
    state = build_state([
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
    ])
    before = list(state.recent)
    result = context_budget(state, max_turns=1, max_chars=100)
    assert len(result["turns"]) == 1
    assert result["turn_count"] == 1
    assert result["max_chars"] == 100
    assert state.recent == before
