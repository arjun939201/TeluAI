from app.melimi.rule_learning import extract_rule_candidates


def test_repeated_plural_examples_produce_reviewable_rule_candidate():
    candidates = extract_rule_candidates([
        {"surface": "సమస్యలు", "source_root": "సమస్య", "target_root": "చిక్కు", "melimi": "చిక్కులు", "evidence_id": "e1"},
        {"surface": "విషయాలు", "source_root": "విషయం", "target_root": "ఎడాటం", "melimi": "ఎడాటాలు", "evidence_id": "e2"},
    ])
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.operation == "plural"
    assert candidate.example_count == 2
    assert candidate.status == "NEEDS_REVIEW"
    assert candidate.confidence == 0.7
    assert candidate.evidence_ids == ("e1", "e2")
    assert candidate.as_dict()["feature_constraints"] == {"number": "plural"}


def test_single_example_is_not_generalized():
    candidates = extract_rule_candidates([
        {"surface": "సమస్యలు", "source_root": "సమస్య", "target_root": "చిక్కు", "melimi": "చిక్కులు", "evidence_id": "e1"},
    ])
    assert candidates == []


def test_unrelated_operations_are_not_merged():
    candidates = extract_rule_candidates([
        {"surface": "సమస్యలు", "source_root": "సమస్య", "target_root": "చిక్కు", "melimi": "చిక్కులు", "evidence_id": "e1"},
        {"surface": "సంతోషానికి", "source_root": "సంతోషం", "target_root": "అలరిక", "melimi": "అలరికకి", "evidence_id": "e2"},
    ])
    assert candidates == []
