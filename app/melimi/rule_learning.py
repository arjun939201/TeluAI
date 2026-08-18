"""Conservative extraction of reusable Melimi rule candidates from evidence.

This module deliberately stops at ``NEEDS_REVIEW``. It can discover that
multiple independent examples share the same *already-known* morphological
operation, but it cannot promote a hypothesis to authoritative grammar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from app.melimi.linguistic_model import analyze_surface


@dataclass(frozen=True)
class RuleEvidence:
    source_surface: str
    target_surface: str
    source_root: str
    target_root: str
    operations: tuple[tuple[str, str], ...]
    evidence_id: str = ""
    source: str = ""


@dataclass(frozen=True)
class GeneralizationCandidate:
    operation: str
    feature_constraints: tuple[tuple[str, str], ...]
    evidence_ids: tuple[str, ...]
    example_count: int
    confidence: float
    status: str = "NEEDS_REVIEW"
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "operation": self.operation,
            "feature_constraints": dict(self.feature_constraints),
            "evidence_ids": list(self.evidence_ids),
            "example_count": self.example_count,
            "confidence": self.confidence,
            "status": self.status,
            "reason": self.reason,
        }


def _evidence_pair(item: Mapping[str, str], evidence_id: str = "") -> RuleEvidence | None:
    source = str(item.get("surface") or item.get("source") or item.get("standard") or "").strip()
    target = str(item.get("target") or item.get("melimi") or "").strip()
    source_root = str(item.get("source_root") or item.get("standard_root") or source).strip()
    target_root = str(item.get("target_root") or item.get("melimi_root") or target).strip()
    if not source or not target or not source_root or not target_root:
        return None
    source_analysis = analyze_surface(source, {source_root: target_root})
    return RuleEvidence(
        source_surface=source,
        target_surface=target,
        source_root=source_analysis.root,
        target_root=target_root,
        operations=source_analysis.operations,
        evidence_id=evidence_id or str(item.get("id") or ""),
        source=str(item.get("provenance") or item.get("source") or ""),
    )


def extract_rule_candidates(examples: Iterable[Mapping[str, str]]) -> list[GeneralizationCandidate]:
    """Find repeated morphological operations without inventing a rule.

    A candidate requires at least two independent examples with the same
    operation signature. Confidence is capped below authority and provenance
    is retained through the evidence ids.
    """

    evidence: list[RuleEvidence] = []
    for item in examples:
        parsed = _evidence_pair(item, str(item.get("evidence_id") or item.get("id") or ""))
        if parsed and parsed.operations:
            evidence.append(parsed)

    groups: dict[tuple[tuple[str, str], ...], list[RuleEvidence]] = {}
    for item in evidence:
        groups.setdefault(item.operations, []).append(item)

    candidates: list[GeneralizationCandidate] = []
    for operations, items in groups.items():
        if len(items) < 2:
            continue
        kinds = {kind for kind, _ in operations}
        if len(kinds) != 1:
            continue
        operation = next(iter(kinds))
        feature_constraints: list[tuple[str, str]] = []
        if operation == "plural":
            feature_constraints.append(("number", "plural"))
        elif operation == "case":
            for _, value in operations:
                feature_constraints.append(("case", value))
        elif operation in {"adjective", "adjective_predicate", "adjective_invariant", "relational_adjective"}:
            feature_constraints.append(("category", "adjective"))
        elif operation == "verb":
            feature_constraints.append(("category", "verb"))
        confidence = min(0.9, 0.5 + 0.1 * len(items))
        ids = tuple(item.evidence_id for item in items if item.evidence_id)
        candidates.append(
            GeneralizationCandidate(
                operation=operation,
                feature_constraints=tuple(feature_constraints),
                evidence_ids=ids,
                example_count=len(items),
                confidence=confidence,
                reason="Repeated supported morphological operation; explicit review is required before publication.",
            )
        )
    return candidates
