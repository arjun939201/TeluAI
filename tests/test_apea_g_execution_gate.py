import pytest

from scripts.apea_g_execution import (
    MAX_REPAIRS,
    ExecutionError,
    ExecutionState,
    ExecutionStatus,
    begin_step,
    ci_green,
    ci_red,
    resume_repair,
    submit_for_ci,
)


def test_green_completes_only_after_ci_pending():
    state = begin_step(ExecutionState("step-1"))
    state = submit_for_ci(state)
    assert ci_green(state).status is ExecutionStatus.COMPLETE


def test_red_repairs_same_step_and_increments_budget():
    state = submit_for_ci(begin_step(ExecutionState("step-1")))
    repaired = ci_red(state)
    assert repaired.step_id == "step-1"
    assert repaired.status is ExecutionStatus.REPAIRING
    assert repaired.repair_attempts == 1
    assert resume_repair(repaired).status is ExecutionStatus.IMPLEMENTING


def test_repair_budget_blocks_instead_of_looping_forever():
    state = ExecutionState("step-1", ExecutionStatus.CI_PENDING, MAX_REPAIRS)
    blocked = ci_red(state)
    assert blocked.status is ExecutionStatus.BLOCKED
    assert blocked.repair_attempts == MAX_REPAIRS


def test_invalid_transitions_fail_closed():
    with pytest.raises(ExecutionError):
        ci_green(ExecutionState("step-1"))
    with pytest.raises(ExecutionError):
        begin_step(ExecutionState("step-1", ExecutionStatus.COMPLETE))
    with pytest.raises(ExecutionError):
        resume_repair(ExecutionState("step-1", ExecutionStatus.CI_PENDING))
