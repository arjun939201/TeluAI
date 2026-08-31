"""Deterministic execution gate used by APEA-G before mutating a plan."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateAction(str, Enum):
    ADVANCE = "advance"
    REPAIR = "repair"
    BLOCK = "block"
    WAIT = "wait"


@dataclass(frozen=True)
class GateDecision:
    action: GateAction
    reason: str


def decide(*, ci_conclusion: str | None, step_status: str, repair_attempts: int, max_repairs: int = 4) -> GateDecision:
    """Return the only safe action for the current persisted execution state."""
    if repair_attempts < 0 or max_repairs <= 0:
        return GateDecision(GateAction.BLOCK, "invalid repair budget")
    if repair_attempts > max_repairs:
        return GateDecision(GateAction.BLOCK, "repair budget exceeded")
    if step_status in {"complete", "blocked"}:
        return GateDecision(GateAction.BLOCK, "step is terminal")
    if ci_conclusion == "success":
        if step_status != "ci_pending":
            return GateDecision(GateAction.BLOCK, "GREEN requires a CI-pending step")
        return GateDecision(GateAction.ADVANCE, "CI passed")
    if ci_conclusion == "failure":
        if step_status not in {"ci_pending", "repairing"}:
            return GateDecision(GateAction.BLOCK, "RED requires an active step")
        if repair_attempts >= max_repairs:
            return GateDecision(GateAction.BLOCK, "repair budget exhausted")
        return GateDecision(GateAction.REPAIR, "CI failed; repair the current step")
    return GateDecision(GateAction.WAIT, "CI result is not final")
