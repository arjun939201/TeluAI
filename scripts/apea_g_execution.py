"""Deterministic execution gate used by APEA-G's autonomous controller.

This module contains no LLM or GitHub side effects. It owns only the legal
state transitions for a plan step so the controller cannot advance on RED,
re-run a completed step, or exceed its repair budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MAX_REPAIRS = 4


class ExecutionStatus(str, Enum):
    READY = "ready"
    IMPLEMENTING = "implementing"
    CI_PENDING = "ci_pending"
    REPAIRING = "repairing"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class ExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionState:
    step_id: str
    status: ExecutionStatus = ExecutionStatus.READY
    repair_attempts: int = 0


def begin_step(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.READY:
        raise ExecutionError(f"cannot begin step from {state.status.value}")
    return ExecutionState(state.step_id, ExecutionStatus.IMPLEMENTING, state.repair_attempts)


def submit_for_ci(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.IMPLEMENTING:
        raise ExecutionError(f"cannot submit for CI from {state.status.value}")
    return ExecutionState(state.step_id, ExecutionStatus.CI_PENDING, state.repair_attempts)


def ci_green(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.CI_PENDING:
        raise ExecutionError(f"GREEN is only valid after CI_PENDING, got {state.status.value}")
    return ExecutionState(state.step_id, ExecutionStatus.COMPLETE, state.repair_attempts)


def ci_red(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.CI_PENDING:
        raise ExecutionError(f"RED is only valid after CI_PENDING, got {state.status.value}")
    if state.repair_attempts >= MAX_REPAIRS:
        return ExecutionState(state.step_id, ExecutionStatus.BLOCKED, state.repair_attempts)
    return ExecutionState(state.step_id, ExecutionStatus.REPAIRING, state.repair_attempts + 1)


def resume_repair(state: ExecutionState) -> ExecutionState:
    if state.status != ExecutionStatus.REPAIRING:
        raise ExecutionError(f"cannot resume repair from {state.status.value}")
    return ExecutionState(state.step_id, ExecutionStatus.IMPLEMENTING, state.repair_attempts)
