"""Deterministic dependency-aware planning engine for APEA-G."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


MAX_STEPS = 12


@dataclass(frozen=True)
class PlanStep:
    id: str
    capability: str
    goal: str
    depends_on: tuple[str, ...] = field(default_factory=tuple)


class PlanningError(ValueError):
    pass


def validate_steps(steps: Iterable[PlanStep]) -> list[PlanStep]:
    result = list(steps)
    if not result:
        raise PlanningError("plan must contain at least one step")
    if len(result) > MAX_STEPS:
        raise PlanningError(f"plan exceeds maximum of {MAX_STEPS} steps")

    ids = [step.id for step in result]
    if len(ids) != len(set(ids)):
        raise PlanningError("plan contains duplicate step ids")

    known = set(ids)
    for step in result:
        if step.id in step.depends_on:
            raise PlanningError(f"step {step.id} cannot depend on itself")
        missing = set(step.depends_on) - known
        if missing:
            raise PlanningError(f"step {step.id} has unknown dependencies: {sorted(missing)}")

    _assert_acyclic(result)
    return result


def _assert_acyclic(steps: list[PlanStep]) -> None:
    graph = {step.id: step.depends_on for step in steps}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise PlanningError("plan dependency cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def ready_steps(steps: Iterable[PlanStep], completed: set[str]) -> list[PlanStep]:
    validated = validate_steps(steps)
    return [
        step
        for step in validated
        if step.id not in completed and set(step.depends_on).issubset(completed)
    ]


def next_step(steps: Iterable[PlanStep], completed: set[str]) -> PlanStep | None:
    ready = ready_steps(steps, completed)
    return ready[0] if ready else None


def build_default_plan() -> list[PlanStep]:
    """Build the next bounded execution plan from the APEA-G roadmap."""
    return validate_steps([
        PlanStep("quality-contract", "quality-evaluation", "Define deterministic quality gates and evaluation contracts"),
        PlanStep("quality-tests", "quality-evaluation", "Expand regression and behavioral evaluation coverage", ("quality-contract",)),
        PlanStep("quality-ci", "quality-evaluation", "Make CI publish actionable quality evidence", ("quality-tests",)),
        PlanStep("performance", "performance", "Measure and improve runtime latency and resource use", ("quality-ci",)),
        PlanStep("security", "security", "Harden secrets, input boundaries, sessions, and dependency posture", ("performance",)),
        PlanStep("ux", "ux", "Improve reliable user-facing behavior and error recovery", ("security",)),
        PlanStep("production", "production", "Harden deployment, health checks, observability, and rollback", ("ux",)),
        PlanStep("release", "release", "Establish release gates and production readiness evidence", ("production",)),
    ])
