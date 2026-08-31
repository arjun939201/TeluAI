import json

import pytest

from scripts.apea_g_state import load_state, record, save_state


def test_state_round_trip(tmp_path, monkeypatch):
    import scripts.apea_g_state as module
    path = tmp_path / "state.json"
    monkeypatch.setattr(module, "STATE_PATH", path)
    state = load_state()
    record(state, sha="abc", capability="quality-evaluation", status="active", action="audit")
    save_state(state)
    assert load_state()["last_green_sha"] == "abc"
    assert load_state()["current_capability"] == "quality-evaluation"
    assert load_state()["attempt"] == 1


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
    for index in range(60):
        record(state, sha=str(index))
    save_state(state)
    assert len(load_state()["history"]) == 50
