import pytest

from scripts.apea_g_planner import PlanStep, PlanningError, next_step, validate_steps


def test_execution_cannot_advance_past_unmet_dependency():
    steps = [
        PlanStep("a", "x", "A"),
        PlanStep("b", "x", "B", ("a",)),
    ]
    assert next_step(steps, set()).id == "a"
    assert next_step(steps, {"b"}) is None


def test_completed_steps_are_not_reselected():
    steps = [
        PlanStep("a", "x", "A"),
        PlanStep("b", "x", "B", ("a",)),
    ]
    assert next_step(steps, {"a"}).id == "b"
    assert next_step(steps, {"a", "b"}) is None


def test_invalid_dependency_graph_fails_before_execution():
    with pytest.raises(PlanningError):
        validate_steps([
            PlanStep("a", "x", "A", ("b",)),
            PlanStep("b", "x", "B", ("a",)),
        ])
