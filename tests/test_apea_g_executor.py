import pytest

from scripts.apea_g_executor import (
    ExecutionError,
    ExecutionState,
    ExecutionStatus,
    finish_repair,
    mark_ci_pending,
    mark_green,
    mark_red,
    start_step,
)
from scripts.apea_g_planner import PlanStep


STEPS = [
    PlanStep("a", "x", "A"),
    PlanStep("b", "x", "B", ("a",)),
]


def test_execution_follows_dependencies():
    state = start_step(STEPS, ExecutionState())
    assert state.current_step == "a"
    assert state.status == ExecutionStatus.IMPLEMENTING
    state = mark_ci_pending(state)
    state = mark_green(STEPS, state)
    assert state.current_step == "b"


def test_red_repairs_same_step_then_returns_to_ci():
    state = start_step(STEPS, ExecutionState())
    state = mark_ci_pending(state)
    state = mark_red(state)
    assert state.current_step == "a"
    assert state.status == ExecutionStatus.REPAIRING
    assert state.repair_attempts == 1
    assert finish_repair(state).status == ExecutionStatus.CI_PENDING


def test_repair_budget_fails_closed():
    state = ExecutionState(frozenset(), "a", ExecutionStatus.CI_PENDING, 4)
    blocked = mark_red(state)
    assert blocked.status == ExecutionStatus.BLOCKED
    assert blocked.current_step == "a"


def test_invalid_transition_fails_closed():
    with pytest.raises(ExecutionError):
        mark_ci_pending(ExecutionState())
