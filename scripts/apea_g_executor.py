"""Deterministic execution state machine for APEA-G plan steps."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from scripts.apea_g_planner import PlanStep, validate_steps


MAX_REPAIRS = 4


class ExecutionStatus(str, Enum):
    READY = "ready"
    IMPLEMENTING = "implementing"
    CI_PENDING = "ci_pending"
    GREEN = "green"
    REPAIRING = "repairing"
    BLOCKED = "blocked"
    COMPLETE = "complete"


@dataclass(frozen=True)
class ExecutionState:
    completed: frozenset[str] = frozenset()
    current_step: str | None = None
    status: ExecutionStatus = ExecutionStatus.READY
    repair_attempts: int = 0


class ExecutionError(ValueError):
    pass


def start_step(steps: Iterable[PlanStep], state: ExecutionState) -> ExecutionState:
    steps = validate_steps(steps)
    if state.status not in {ExecutionStatus.READY, ExecutionStatus.GREEN}:
        raise ExecutionError(f"cannot start from {state.status.value}")
    completed = set(state.completed)
    for step in steps:
        if step.id not in completed and set(step.depends_on).issubset(completed):
            return ExecutionState(state.completed, step.id, ExecutionStatus.IMPLEMENTING, 0)
    return ExecutionState(state.completed, None, ExecutionStatus.COMPLETE, 0)


def mark_ci_pending(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.IMPLEMENTING or not state.current_step:
        raise ExecutionError("only an implementing step can enter CI")
    return ExecutionState(state.completed, state.current_step, ExecutionStatus.CI_PENDING, state.repair_attempts)


def mark_green(steps: Iterable[PlanStep], state: ExecutionState) -> ExecutionState:
    steps = validate_steps(steps)
    if state.status != ExecutionStatus.CI_PENDING or not state.current_step:
        raise ExecutionError("only a CI-pending step can become green")
    completed = set(state.completed)
    completed.add(state.current_step)
    next_state = ExecutionState(frozenset(completed), None, ExecutionStatus.GREEN, 0)
    return start_step(steps, next_state)


def mark_red(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.CI_PENDING or not state.current_step:
        raise ExecutionError("only a CI-pending step can be repaired")
    if state.repair_attempts >= MAX_REPAIRS:
        return ExecutionState(state.completed, state.current_step, ExecutionStatus.BLOCKED, state.repair_attempts)
    return ExecutionState(state.completed, state.current_step, ExecutionStatus.REPAIRING, state.repair_attempts + 1)


def finish_repair(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.REPAIRING or not state.current_step:
        raise ExecutionError("only a repairing step can return to CI")
    return ExecutionState(state.completed, state.current_step, ExecutionStatus.CI_PENDING, state.repair_attempts)
