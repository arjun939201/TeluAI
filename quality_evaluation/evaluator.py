"""Core quality-evaluation engine with deterministic metric hooks."""
from __future__ import annotations

from collections.abc import Callable

from .schema import QualityEvaluation, QualityMetric

MetricFunction = Callable[[str, str], QualityMetric]


class QualityEvaluator:
    """Evaluate a generated response through explicit metric implementations.

    The default implementation is intentionally conservative: metric hooks are
    deterministic placeholders until a production evaluator is selected. This
    keeps the public contract stable without pretending that heuristic scores
    are factual judgments.
    """

    VERSION = "0.1"

    def __init__(self, *, metrics: dict[str, MetricFunction] | None = None) -> None:
        self._metrics = metrics or {}

    def evaluate(self, prompt: str, response: str) -> QualityEvaluation:
        """Return all required metrics using registered hooks or safe defaults."""
        results: dict[str, QualityMetric] = {}
        for name in ("relevance", "coherence", "factual_accuracy", "toxicity"):
            function = self._metrics.get(name)
            results[name] = function(prompt, response) if function else self._not_evaluated(name)

        overall = sum(metric.score for metric in results.values()) / len(results)
        return QualityEvaluation(
            relevance=results["relevance"],
            coherence=results["coherence"],
            factual_accuracy=results["factual_accuracy"],
            toxicity=results["toxicity"],
            overall_score=round(overall, 6),
            evaluator_version=self.VERSION,
        )

    @staticmethod
    def _not_evaluated(name: str) -> QualityMetric:
        return QualityMetric(
            score=0.0,
            rationale=f"{name} evaluator is not configured yet.",
        )
