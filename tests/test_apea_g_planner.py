import pytest

from scripts.apea_g_planner import (
    PlanStep,
    PlanningError,
    build_default_plan,
    next_step,
    ready_steps,
    validate_steps,
)


def test_default_plan_is_bounded_and_dependency_ordered():
    steps = build_default_plan()
    assert len(steps) <= 12
    assert steps[0].id == "quality-contract"
    assert steps[-1].id == "release"
    validate_steps(steps)


def test_next_step_waits_for_dependencies():
    steps = build_default_plan()
    assert next_step(steps, set()).id == "quality-contract"
    completed = {"quality-contract"}
    assert next_step(steps, completed).id == "quality-tests"


def test_ready_steps_can_expose_parallel_work():
    steps = [
        PlanStep("a", "x", "A"),
        PlanStep("b", "x", "B"),
        PlanStep("c", "x", "C", ("a", "b")),
    ]
    assert [s.id for s in ready_steps(steps, set())] == ["a", "b"]
    assert [s.id for s in ready_steps(steps, {"a", "b"})] == ["c"]


def test_unknown_dependency_and_cycle_fail_closed():
    with pytest.raises(PlanningError):
        validate_steps([PlanStep("a", "x", "A", ("missing",))])
    with pytest.raises(PlanningError):
        validate_steps([
            PlanStep("a", "x", "A", ("b",)),
            PlanStep("b", "x", "B", ("a",)),
        ])


def test_plan_limit_is_enforced():
    steps = [PlanStep(str(i), "x", "step") for i in range(13)]
    with pytest.raises(PlanningError):
        validate_steps(steps)
