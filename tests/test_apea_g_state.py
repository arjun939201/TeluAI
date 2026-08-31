import json

import pytest

from scripts.apea_g_state import (
    load_plan,
    load_roadmap,
    load_state,
    next_capability,
    record,
    save_plan,
    save_state,
    set_capability_status,
)


def test_state_round_trip(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "state.json"
    monkeypatch.setattr(module, "STATE_PATH", path)
    state = load_state()
    record(state, sha="abc", capability="quality-evaluation", status="active", action="audit", step=2)
    save_state(state)
    loaded = load_state()
    assert loaded["schema_version"] == 3
    assert loaded["last_green_sha"] == "abc"
    assert loaded["current_capability"] == "quality-evaluation"
    assert loaded["current_step"] == 2
    assert loaded["attempt"] == 1


def test_invalid_schema_fails_closed(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    monkeypatch.setattr(module, "STATE_PATH", path)
    with pytest.raises(ValueError):
        load_state()


def test_history_is_bounded(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "state.json"
    monkeypatch.setattr(module, "STATE_PATH", path)
    state = load_state()
    for index in range(120):
        record(state, sha=str(index))
    save_state(state)
    assert len(load_state()["history"]) == 100


def test_plan_is_bounded_and_round_trips(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "plan.json"
    monkeypatch.setattr(module, "PLAN_PATH", path)
    plan = {"schema_version": 1, "plan_id": "p1", "steps": [{"id": "one", "goal": "test"}]}
    save_plan(plan)
    assert load_plan() == plan


def test_plan_rejects_more_than_twelve_steps(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "plan.json"
    monkeypatch.setattr(module, "PLAN_PATH", path)
    plan = {"schema_version": 1, "steps": [{"id": str(i)} for i in range(13)]}
    with pytest.raises(ValueError):
        save_plan(plan)


def test_roadmap_selection_and_status(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "roadmap.json"
    monkeypatch.setattr(module, "ROADMAP_PATH", path)
    roadmap = load_roadmap()
    assert next_capability(roadmap) == "quality-evaluation"
    set_capability_status(roadmap, "quality-evaluation", "complete")
    assert next_capability(roadmap) == "performance"


def test_roadmap_rejects_unknown_capability(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "roadmap.json"
    monkeypatch.setattr(module, "ROADMAP_PATH", path)
    with pytest.raises(ValueError):
        set_capability_status(load_roadmap(), "does-not-exist", "complete")
