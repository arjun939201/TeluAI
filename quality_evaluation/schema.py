"""Pydantic contracts for TeluAI output-quality evaluation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MetricName = Literal["relevance", "coherence", "factual_accuracy", "toxicity"]


class QualityMetric(BaseModel):
    """A normalized metric result on a 0..1 scale."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=2000)


class QualityEvaluation(BaseModel):
    """Stable response-quality contract used by evaluators and API layers."""

    model_config = ConfigDict(extra="forbid")

    relevance: QualityMetric
    coherence: QualityMetric
    factual_accuracy: QualityMetric
    toxicity: QualityMetric
    overall_score: float = Field(ge=0.0, le=1.0)
    evaluator_version: str = Field(min_length=1, max_length=64)

    @property
    def metrics(self) -> dict[MetricName, QualityMetric]:
        return {
            "relevance": self.relevance,
            "coherence": self.coherence,
            "factual_accuracy": self.factual_accuracy,
            "toxicity": self.toxicity,
        }
