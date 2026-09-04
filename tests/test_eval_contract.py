import json

from app.eval import CASES, run


def test_language_evaluation_corpus_has_unique_case_ids():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    ids = [str(case.get("id", "")) for case in cases]
    assert ids
    assert all(ids)
    assert len(ids) == len(set(ids))


def test_language_evaluation_covers_all_deterministic_metrics():
    result = run()
    assert result["cases"] > 0
    assert result["failures"] == []
    measured = result["measured"]
    for metric in (
        "intent_cases",
        "language_cases",
        "mode_cases",
        "morphology_cases",
        "unsupported_cases",
        "authority_cases",
        "retrieval_cases",
    ):
        assert measured[metric] > 0
