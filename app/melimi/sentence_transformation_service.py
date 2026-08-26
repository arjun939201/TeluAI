"""Service boundary for auditable sentence-level Melimi conversion."""
from __future__ import annotations

from app.melimi.sentence_transformation import transform_sentence, validate_transformation
from app.melimi.sentence_transformation_contract import SentenceTransformation, TransformationIssue


def transform_for_response(text: str) -> SentenceTransformation:
    result = transform_sentence(text)
    validation = validate_transformation(result)
    issues = tuple(
        TransformationIssue(token="", reason=reason)
        for reason in validation["violations"]
    )
    return SentenceTransformation(
        source=result["source"],
        transformed=result["transformed"],
        changed_tokens=result["changed_tokens"],
        unresolved_tokens=tuple(result["unresolved_tokens"]),
        issues=issues,
    )
