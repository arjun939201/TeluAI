from __future__ import annotations

import pytest
from pydantic import ValidationError

from quality_evaluation.schema import QualityEvaluation, QualityMetric


def metric() -> QualityMetric:
    return QualityMetric(score=0.8, rationale="The response is clear and useful.")


def test_quality_evaluation_contract_accepts_normalized_metrics() -> None:
    evaluation = QualityEvaluation(
        relevance=metric(),
        coherence=metric(),
        factual_accuracy=metric(),
        toxicity=metric(),
        overall_score=0.8,
        evaluator_version="0.1",
    )

    assert set(evaluation.metrics) == {
        "relevance",
        "coherence",
        "factual_accuracy",
        "toxicity",
    }
    assert evaluation.overall_score == 0.8


def test_quality_metric_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        QualityMetric(score=1.01, rationale="invalid")


def test_quality_evaluation_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        QualityEvaluation(
            relevance=metric(),
            coherence=metric(),
            factual_accuracy=metric(),
            toxicity=metric(),
            overall_score=0.8,
            evaluator_version="0.1",
            unexpected="drift",
        )
