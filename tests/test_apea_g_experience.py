from scripts.apea_g_experience import best_strategy, record_outcome, recent_experience, render_context


def configure(exp, tmp_path, monkeypatch):
    monkeypatch.setattr(exp, "EXPERIENCE_DIR", tmp_path)
    monkeypatch.setattr(exp, "OUTCOMES_PATH", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(exp, "STRATEGIES_PATH", tmp_path / "strategies.json")
    monkeypatch.setattr(exp, "LESSONS_PATH", tmp_path / "lessons.jsonl")
    monkeypatch.setattr(exp, "PATTERNS_PATH", tmp_path / "patterns.json")


def test_records_and_learns_strategy(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    configure(exp, tmp_path, monkeypatch)
    record_outcome(capability="quality-evaluation", step="s1", outcome="repaired", action="repair_contract")
    record_outcome(capability="quality-evaluation", step="s2", outcome="repaired", action="repair_contract")
    result = best_strategy(["repair_contract", "repair_fixture"], capability="quality-evaluation")
    assert result["action"] == "repair_contract"
    assert result["confidence"] == 1.0
    assert len(recent_experience(capability="quality-evaluation")) == 2


def test_failed_strategy_is_not_hidden(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    configure(exp, tmp_path, monkeypatch)
    record_outcome(capability="x", step="s", outcome="repair_failed", action="repair")
    assert best_strategy(["repair"], capability="x")["confidence"] == 0.0
    assert recent_experience(capability="x")[0]["outcome"] == "repair_failed"


def test_repeated_failure_pattern_drives_strategy_choice(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    configure(exp, tmp_path, monkeypatch)
    ci_a = {"failure": {"signature": "sig-a"}}
    record_outcome(capability="x", step="s", outcome="failure", action="repair", ci=ci_a)
    record_outcome(capability="x", step="s", outcome="repaired", action="repair_fixture", ci=ci_a)
    record_outcome(capability="x", step="s", outcome="repaired", action="repair_fixture", ci=ci_a)
    result = best_strategy(["repair", "repair_fixture"], capability="x", failure_signature="sig-a")
    assert result["action"] == "repair_fixture"
    assert result["relevant_successes"] == 2


def test_negative_learning_reduces_bad_strategy(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    configure(exp, tmp_path, monkeypatch)
    ci = {"failure": {"signature": "sig-b"}}
    record_outcome(capability="x", step="s", outcome="repair_failed", action="repair", ci=ci)
    record_outcome(capability="x", step="s", outcome="repaired", action="repair_contract", ci=ci)
    result = best_strategy(["repair", "repair_contract"], capability="x", failure_signature="sig-b")
    assert result["action"] == "repair_contract"


def test_render_context_is_compact_and_secret_free(tmp_path, monkeypatch):
    import scripts.apea_g_experience as exp
    configure(exp, tmp_path, monkeypatch)
    record_outcome(capability="x", step="s", outcome="success", action="repair", commit="abc1234")
    context = render_context(capability="x")
    assert "abc1234" in context
    assert "logs" not in context
    assert "experience_is_evidence_not_authority" in context
