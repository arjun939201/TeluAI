"""Typed, conservative executable Melimi rule contracts.

Rules describe reusable grammatical operations; they do not create lexical
authority. MASTER/approved status and explicit feature constraints are required
before a rule can be applied. Surface realization is delegated to the existing
root-first morphology engine so there is still one morphology source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.melimi.root_morphology import MorphologicalForm, reapply_operations

_ALLOWED_OPERATIONS = {
    "plural",
    "case",
    "adjective",
    "adjective_predicate",
    "adjective_invariant",
    "relational_adjective",
    "verb",
    "derived_voice",
    "derivation",
}
_AUTHORITY = {"MASTER", "APPROVED", "VERIFIED"}


@dataclass(frozen=True)
class MelimiRule:
    """A reusable linguistic rule backed by explicit constraints.

    ``operation`` names an operation already understood by the deterministic
    morphology engine. The rule itself never invents a new surface algorithm.
    """

    name: str
    category: str
    operation: str
    constraints: tuple[tuple[str, str], ...] = ()
    status: str = "MASTER"
    authority: str = "MASTER"
    source: str = ""
    version: int | None = None
    confidence: float = 1.0
    evidence_ids: tuple[str, ...] = ()

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "MelimiRule":
        raw_constraints = record.get("constraints") or record.get("feature_constraints") or {}
        if isinstance(raw_constraints, Mapping):
            constraints = tuple(sorted((str(k), str(v)) for k, v in raw_constraints.items()))
        else:
            constraints = tuple((str(k), str(v)) for k, v in raw_constraints)
        raw_ids = record.get("evidence_ids") or ()
        return cls(
            name=str(record.get("name") or "").strip(),
            category=str(record.get("category") or "").strip(),
            operation=str(record.get("operation") or "").strip(),
            constraints=constraints,
            status=str(record.get("status") or "").upper(),
            authority=str(record.get("authority") or record.get("status") or "").upper(),
            source=str(record.get("source") or ""),
            version=record.get("version"),
            confidence=max(0.0, min(1.0, float(record.get("confidence", 1.0)))),
            evidence_ids=tuple(str(x) for x in raw_ids if str(x).strip()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "operation": self.operation,
            "constraints": dict(self.constraints),
            "status": self.status,
            "authority": self.authority,
            "source": self.source,
            "version": self.version,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
        }

    def supports(self, features: Mapping[str, Any]) -> bool:
        """Return whether this rule may operate on the supplied features."""
        if self.operation not in _ALLOWED_OPERATIONS:
            return False
        if self.status not in _AUTHORITY or self.authority not in _AUTHORITY:
            return False
        for key, expected in self.constraints:
            actual = features.get(key)
            if actual is None or str(actual) != expected:
                return False
        return True

    def realize(self, target_root: str, analysis: Any) -> str | None:
        """Apply this rule through the existing deterministic morphology layer.

        The operation must match an operation represented by the analysis, or
        be justified by an explicit feature constraint. This prevents a rule
        from being used as a free-form word generator.
        """
        if not target_root or not self.supports(analysis.features.as_dict()):
            return None

        operations = list(analysis.operations)
        if self.operation in {kind for kind, _ in operations}:
            selected = [(kind, value) for kind, value in operations if kind == self.operation]
        elif self.operation == "case" and analysis.features.case:
            selected = [("case", analysis.features.case)]
        elif self.operation == "plural" and analysis.features.number == "plural":
            selected = [("plural", "లు")]
        else:
            return None

        form = MorphologicalForm(
            surface=analysis.surface,
            root=analysis.root,
            suffixes=tuple(value for _, value in selected),
            kinds=tuple(kind for kind, _ in selected),
        )
        return reapply_operations(target_root, form)


def load_master_rules(limit: int = 100) -> tuple[MelimiRule, ...]:
    """Load only authoritative runtime rules from the existing Language Space."""
    from app.melimi.db_subject import language_rules

    rules: list[MelimiRule] = []
    for record in language_rules(limit=limit):
        rule = MelimiRule.from_record(record)
        if rule.status in _AUTHORITY and rule.operation in _ALLOWED_OPERATIONS:
            rules.append(rule)
    return tuple(rules)
