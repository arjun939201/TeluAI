"""Typed linguistic contracts for generalized Melimi transformation.

This module does not replace the existing morphology engine. It gives the
existing root-first pipeline an explicit domain vocabulary so lexical mapping,
morphology, evidence and transformation decisions are no longer passed around
as loosely structured dictionaries or raw operation strings.

The contracts are intentionally small. Unsupported features remain ``None``
rather than being guessed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from app.melimi.root_morphology import MorphologicalForm, convert_surface, reduce_to_root, reapply_operations


@dataclass(frozen=True)
class MorphologicalFeatures:
    """Grammatical features recovered from a surface form.

    Only features actually established by the current deterministic analyzer
    are populated. The remaining dimensions are reserved for future grammar
    modules and deliberately stay ``None`` instead of being inferred.
    """

    number: str | None = None
    case: str | None = None
    derivation: str | None = None
    category: str | None = None
    tense: str | None = None
    aspect: str | None = None
    mood: str | None = None
    polarity: str | None = None
    voice: str | None = None
    person: str | None = None
    gender: str | None = None
    honorificity: str | None = None
    participial_status: str | None = None
    clitics: tuple[str, ...] = ()
    postpositions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LexicalEntry:
    """A lemma-level lexical relationship.

    ``standard_lemma`` and ``melimi_lemma`` are the reusable lexical units.
    Surface forms must be generated from these lemmas plus grammatical
    features; they are not stored here as independent dictionary mappings.
    """

    standard_lemma: str
    melimi_lemma: str
    part_of_speech: str | None = None
    semantic_class: str | None = None
    morphological_class: str | None = None
    inflection_class: str | None = None
    derivation_class: str | None = None
    semantic_relation: str | None = None
    confidence: float = 1.0
    source: str = ""
    authority: str = "MASTER"
    version: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransformationEvidence:
    """Why a lexical/morphological transformation is allowed."""

    source: str
    authority: str
    confidence: float
    version: int | None = None
    rule_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinguisticAnalysis:
    """Structured analysis of one surface form."""

    surface: str
    root: str
    operations: tuple[tuple[str, str], ...]
    features: MorphologicalFeatures

    @classmethod
    def from_form(cls, form: MorphologicalForm) -> "LinguisticAnalysis":
        case = None
        number = None
        derivation = None
        category = None
        for kind, value in form.operations:
            if kind == "case":
                case = value
            elif kind == "plural":
                number = "plural"
            elif kind in {"derivation", "adjective", "adjective_invariant", "adjective_predicate", "relational_adjective"}:
                derivation = value
                category = "adjective" if "adjective" in kind else category
            elif kind in {"verb", "derived_voice"}:
                category = "verb"
                if kind == "derived_voice":
                    derivation = value
        if number is None and not form.operations:
            number = "singular"
        return cls(
            surface=form.surface,
            root=form.root,
            operations=form.operations,
            features=MorphologicalFeatures(
                number=number,
                case=case,
                derivation=derivation,
                category=category,
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operations"] = [
            {"kind": kind, "value": value} for kind, value in self.operations
        ]
        return payload


@dataclass(frozen=True)
class TransformationResult:
    """Traceable result of applying an authoritative lemma mapping."""

    source_surface: str
    source_lemma: str
    target_lemma: str
    target_surface: str
    analysis: LinguisticAnalysis
    evidence: TransformationEvidence | None
    status: str
    reason: str
    generated: bool = False

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["analysis"] = self.analysis.as_dict()
        payload["evidence"] = self.evidence.as_dict() if self.evidence else None
        return payload


def lexical_entry(
    standard_lemma: str,
    melimi_lemma: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> LexicalEntry:
    """Build a typed lexical entry from existing Language Space metadata."""

    data = dict(metadata or {})
    authority = str(data.get("authority") or data.get("status") or "MASTER").upper()
    confidence = data.get("confidence", 1.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 1.0
    return LexicalEntry(
        standard_lemma=standard_lemma,
        melimi_lemma=melimi_lemma,
        part_of_speech=data.get("part_of_speech") or data.get("pos"),
        semantic_class=data.get("semantic_class"),
        morphological_class=data.get("morphological_class"),
        inflection_class=data.get("inflection_class"),
        derivation_class=data.get("derivation_class"),
        semantic_relation=data.get("semantic_relation"),
        confidence=confidence,
        source=str(data.get("source") or ""),
        authority=authority,
        version=data.get("version"),
    )


def analyze_surface(word: str, roots: Mapping[str, str] | None = None) -> LinguisticAnalysis:
    """Analyze a surface form using the existing root-first analyzer."""

    form = reduce_to_root(word, dict(roots) if roots is not None else None)
    return LinguisticAnalysis.from_form(form)


def transform_surface(
    word: str,
    roots: Mapping[str, str] | None = None,
    *,
    evidence: TransformationEvidence | None = None,
) -> TransformationResult:
    """Transform one surface form while preserving its analyzed operations.

    This is deliberately conservative: if the source lemma is not an
    authoritative root, the original surface form is returned unchanged.
    """

    root_map = dict(roots) if roots is not None else None
    analysis = analyze_surface(word, root_map)
    target_lemma = (root_map or {}).get(analysis.root, "")
    if not target_lemma:
        return TransformationResult(
            source_surface=word,
            source_lemma=analysis.root,
            target_lemma="",
            target_surface=word,
            analysis=analysis,
            evidence=None,
            status="UNSUPPORTED",
            reason="No authoritative Melimi lemma exists for the analyzed source root.",
            generated=False,
        )

    target_surface = reapply_operations(target_lemma, MorphologicalForm(
        surface=analysis.surface,
        root=analysis.root,
        suffixes=tuple(value for _, value in analysis.operations),
        kinds=tuple(kind for kind, _ in analysis.operations),
    ))
    return TransformationResult(
        source_surface=word,
        source_lemma=analysis.root,
        target_lemma=target_lemma,
        target_surface=target_surface,
        analysis=analysis,
        evidence=evidence,
        status="MASTER" if evidence is None or evidence.authority == "MASTER" else "SUPPORTED",
        reason="Applied the authoritative lemma mapping and regenerated the analyzed operations.",
        generated=target_surface != target_lemma,
    )
