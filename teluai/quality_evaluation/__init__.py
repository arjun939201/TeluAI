"""Quality Evaluation package.

Provides the core :class:`QualityEvaluator` and the Pydantic schema
:class:`QualityMetrics` used throughout the project.
"""

from .evaluator import QualityEvaluator, QualityMetrics

__all__ = ["QualityEvaluator", "QualityMetrics"]
