from scripts.apea_g_experience import best_strategy, record_outcome, recent_experience, render_context


def test_records_and_learns_strategy(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    monkeypatch.setattr(exp, "EXPERIENCE_DIR", tmp_path)
    monkeypatch.setattr(exp, "OUTCOMES_PATH", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(exp, "STRATEGIES_PATH", tmp_path / "strategies.json")
    monkeypatch.setattr(exp, "LESSONS_PATH", tmp_path / "lessons.jsonl")

    record_outcome(capability="quality-evaluation", step="s1", outcome="repaired", action="repair_contract")
    record_outcome(capability="quality-evaluation", step="s2", outcome="repaired", action="repair_contract")
    result = best_strategy(["repair_contract", "repair_fixture"], capability="quality-evaluation")
    assert result["action"] == "repair_contract"
    assert result["confidence"] == 1.0
    assert len(recent_experience(capability="quality-evaluation")) == 2


def test_failed_strategy_is_not_hidden(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    monkeypatch.setattr(exp, "OUTCOMES_PATH", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(exp, "STRATEGIES_PATH", tmp_path / "strategies.json")
    monkeypatch.setattr(exp, "LESSONS_PATH", tmp_path / "lessons.jsonl")
    record_outcome(capability="x", step="s", outcome="repair_failed", action="repair")
    assert best_strategy(["repair"], capability="x")["confidence"] == 0.0
    assert recent_experience(capability="x")[0]["outcome"] == "repair_failed"


def test_render_context_is_compact_and_secret_free(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    monkeypatch.setattr(exp, "OUTCOMES_PATH", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(exp, "STRATEGIES_PATH", tmp_path / "strategies.json")
    monkeypatch.setattr(exp, "LESSONS_PATH", tmp_path / "lessons.jsonl")
    record_outcome(capability="x", step="s", outcome="success", action="repair", commit="abc1234")
    context = render_context(capability="x")
    assert "abc1234" in context
    assert "logs" not in context
