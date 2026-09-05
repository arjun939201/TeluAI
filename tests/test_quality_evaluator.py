from __future__ import annotations

from quality_evaluation.evaluator import QualityEvaluator
from quality_evaluation.schema import QualityMetric


def test_evaluator_exposes_all_required_metric_hooks() -> None:
    evaluator = QualityEvaluator()
    result = evaluator.evaluate("What is Telugu?", "Telugu is a Dravidian language.")

    assert set(result.metrics) == {
        "relevance",
        "coherence",
        "factual_accuracy",
        "toxicity",
    }
    assert result.evaluator_version == "0.1"


def test_evaluator_uses_registered_metric_function() -> None:
    def relevance(prompt: str, response: str) -> QualityMetric:
        assert prompt == "question"
        assert response == "answer"
        return QualityMetric(score=0.9, rationale="Directly addresses the question.")

    result = QualityEvaluator(metrics={"relevance": relevance}).evaluate("question", "answer")

    assert result.relevance.score == 0.9
    assert result.overall_score == 0.225
