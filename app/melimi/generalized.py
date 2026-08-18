"""Generalized Melimi Telugu linguistic engine.

This module is deliberately independent from the LLM.  It models Melimi
knowledge as structured lexical evidence plus reusable morphological rules.
The existing root-first Telugu analyser remains the low-level morphology
implementation; this layer adds linguistic metadata, provenance, confidence,
and a strict "generalize only when supported" boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from app.melimi.root_morphology import MorphologicalForm, reduce_to_root, reapply_operations

TELUGU_TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")


@dataclass(frozen=True)
class LexicalEntry:
    standard_lemma: str
    melimi_lemma: str
    part_of_speech: str = ""
    semantic_class: str = ""
    morphological_class: str = ""
    inflection_class: str = ""
    derivation_class: str = ""
    semantic_relation: str = "lexical_equivalent"
    confidence: float = 1.0
    source: str = ""
    approval_status: str = "MASTER"
    examples: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    kind: str
    source: str
    confidence: float
    detail: str = ""


@dataclass(frozen=True)
class TransformationTrace:
    source: str
    source_lemma: str
    target_lemma: str
    output: str
    operations: tuple[tuple[str, str], ...] = ()
    evidence: tuple[Evidence, ...] = ()
    generalized: bool = False
    approved: bool = False
    reason: str = ""


@dataclass(frozen=True)
class _MorphRule:
    """A reusable realization rule, not a word-specific mapping."""

    name: str
    kind: str
    confidence: float
    source: str


# These are grammatical realizations, not Melimi vocabulary.  They only run
# after an approved lexical root mapping has been found.  A derivational rule
# is intentionally conservative: it covers the documented Telugu adjective
# pattern X + మైన and its productive Melimi realization when the target root
# ends in ి (e.g. విస్తారం -> విరివి, విస్తారమైన -> విరివైన).
_MORPH_RULES = (
    _MorphRule("telugu.inflection.reapply", "inflection", 0.99, "built-in:telugu-morphology"),
    _MorphRule("telugu.adjective.i-to-ain", "adjective", 0.95, "built-in:telugu-morphology"),
)


def _normalise_status(value: str) -> str:
    return str(value or "").strip().upper()


def _normalise_confidence(value: object, default: float = 1.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _entry_from_record(record: Mapping[str, object]) -> LexicalEntry | None:
    standard = str(
        record.get("standard_lemma")
        or record.get("standard")
        or record.get("standard_or_source")
        or record.get("source_word")
        or ""
    ).strip()
    melimi = str(record.get("melimi_lemma") or record.get("melimi") or record.get("word") or "").strip()
    if not standard or not melimi:
        return None
    return LexicalEntry(
        standard_lemma=standard,
        melimi_lemma=melimi,
        part_of_speech=str(record.get("part_of_speech") or record.get("pos") or ""),
        semantic_class=str(record.get("semantic_class") or ""),
        morphological_class=str(record.get("morphological_class") or ""),
        inflection_class=str(record.get("inflection_class") or ""),
        derivation_class=str(record.get("derivation_class") or ""),
        semantic_relation=str(record.get("semantic_relation") or "lexical_equivalent"),
        confidence=_normalise_confidence(record.get("confidence"), 1.0),
        source=str(record.get("source") or ""),
        approval_status=_normalise_status(record.get("approval_status") or record.get("status")) or "MASTER",
        examples=tuple(str(x) for x in record.get("examples", ()) if str(x).strip()) if isinstance(record.get("examples"), (list, tuple)) else (),
        exceptions=tuple(str(x) for x in record.get("exceptions", ()) if str(x).strip()) if isinstance(record.get("exceptions"), (list, tuple)) else (),
    )


class GeneralizedMelimiEngine:
    """Apply authoritative Melimi lexical knowledge to unseen forms.

    The engine never creates a lexical mapping from spelling similarity.  A
    token can be transformed only when its analysed lemma has an approved
    lexical entry.  Morphology is then regenerated from the target lemma.
    """

    def __init__(
        self,
        lexical_entries: Iterable[LexicalEntry | Mapping[str, object]] = (),
        *,
        roots: Mapping[str, str] | None = None,
        min_confidence: float = 0.75,
    ) -> None:
        entries: dict[str, LexicalEntry] = {}
        for item in lexical_entries:
            entry = item if isinstance(item, LexicalEntry) else _entry_from_record(item)
            if entry is None:
                continue
            if _normalise_status(entry.approval_status) not in {"MASTER", "APPROVED", "ESTABLISHED", "CORPUS-SUPPORTED", "DERIVED-BY-RULE"}:
                continue
            if entry.confidence < min_confidence:
                continue
            entries[entry.standard_lemma] = entry
        if roots:
            for source, target in roots.items():
                source = str(source).strip()
                target = str(target).strip()
                if source and target and source not in entries:
                    entries[source] = LexicalEntry(
                        standard_lemma=source,
                        melimi_lemma=target,
                        confidence=1.0,
                        source="Language Space:MASTER root",
                        approval_status="MASTER",
                    )
        self.entries = entries
        self.roots = {entry.standard_lemma: entry.melimi_lemma for entry in entries.values()}
        self._rules = {rule.name: rule for rule in _MORPH_RULES}

    @classmethod
    def from_root_mapping(cls, roots: Mapping[str, str], **kwargs) -> "GeneralizedMelimiEngine":
        return cls(roots=roots, **kwargs)

    def _entry_for(self, root: str) -> LexicalEntry | None:
        return self.entries.get(root)

    @staticmethod
    def _generate_target(entry: LexicalEntry, form: MorphologicalForm) -> tuple[str, list[Evidence]]:
        target = entry.melimi_lemma
        evidence = [Evidence("lexical", entry.source or "Language Space", entry.confidence, f"{entry.standard_lemma} => {entry.melimi_lemma}")]
        if not form.operations:
            return target, evidence

        # Most inflectional operations are structurally portable between the
        # source and target root.  Reapply them through the existing morphology
        # generator rather than storing every surface form.
        if all(kind != "adjective" for kind, _ in form.operations):
            return reapply_operations(target, form), evidence + [
                Evidence("morphology", _MORPH_RULES[0].source, _MORPH_RULES[0].confidence, "reapplied analysed inflectional features")
            ]

        result = target
        for kind, suffix in form.operations:
            if kind == "adjective" and suffix == "మైన":
                if target.endswith("ి"):
                    result = target[:-1] + "ైన"
                    evidence.append(Evidence("derivation", _MORPH_RULES[1].source, _MORPH_RULES[1].confidence, "-మైన adjective realized as target-final-ి -> -ైన"))
                else:
                    # Do not invent an unsupported derived form for other target
                    # shapes.  The caller will preserve the source surface.
                    return entry.standard_lemma, evidence
            else:
                result = reapply_operations(result, MorphologicalForm(form.surface, target, (suffix,), (kind,)))
        return result, evidence

    def transform_word(self, word: str) -> TransformationTrace:
        surface = (word or "").strip()
        if not surface:
            return TransformationTrace(surface, "", "", surface, reason="empty input")

        form = reduce_to_root(surface, self.roots)
        entry = self._entry_for(form.root)
        if entry is None:
            return TransformationTrace(surface, form.root, "", surface, operations=form.operations, reason="no approved lexical evidence")

        if surface in entry.exceptions:
            return TransformationTrace(surface, form.root, entry.melimi_lemma, surface, operations=form.operations, approved=True, reason="lexical exception")

        output, evidence = self._generate_target(entry, form)
        if output == entry.standard_lemma and form.operations:
            return TransformationTrace(surface, form.root, entry.melimi_lemma, surface, operations=form.operations, evidence=tuple(evidence), approved=True, reason="unsupported target realization; preserved")
        return TransformationTrace(
            surface,
            form.root,
            entry.melimi_lemma,
            output,
            operations=form.operations,
            evidence=tuple(evidence),
            generalized=bool(form.operations),
            approved=True,
            reason="approved lexical mapping + morphological regeneration",
        )

    def transform_text(self, text: str) -> str:
        return TELUGU_TOKEN_RE.sub(lambda match: self.transform_word(match.group(0)).output, text or "")

    def audit_text(self, text: str) -> list[TransformationTrace]:
        return [self.transform_word(token) for token in TELUGU_TOKEN_RE.findall(text or "")]

    def explain_word(self, word: str) -> dict[str, object]:
        trace = self.transform_word(word)
        return {
            "word": trace.source,
            "root": trace.source_lemma,
            "melimi_root": trace.target_lemma,
            "output": trace.output,
            "operations": [{"kind": kind, "feature": feature} for kind, feature in trace.operations],
            "generalized": trace.generalized,
            "approved": trace.approved,
            "reason": trace.reason,
            "evidence": [
                {"kind": item.kind, "source": item.source, "confidence": item.confidence, "detail": item.detail}
                for item in trace.evidence
            ],
        }


def build_engine_from_language_space(*, roots: Mapping[str, str], records: Iterable[Mapping[str, object]] = ()) -> GeneralizedMelimiEngine:
    """Build an engine from the same structured records exposed by Language Space."""
    return GeneralizedMelimiEngine(records, roots=roots)
