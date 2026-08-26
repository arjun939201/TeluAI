"""Deterministic structured ingestion for explicit Melimi Telugu material.

The parser classifies human-written assertions without treating observations or
LLM guesses as authoritative language knowledge.  Source evidence is retained
so downstream stores can apply their own authority policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re


_MAPPING = re.compile(r"^\s*(?P<source>[^=→➜⇒]+?)\s*(?:=|→|➜|⇒|->)\s*(?P<target>.+?)\s*$")
_LABEL = re.compile(
    r"^\s*(?P<label>root|affix|prefix|suffix|grammar|rule|meaning|example|phrase|word|vocabulary)\s*:\s*(?P<value>.+?)\s*$",
    re.I,
)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_PAREN_LABEL = re.compile(r"\s*\((?P<label>root|affix|prefix|suffix|grammar|rule|example|phrase|word)\)\s*$", re.I)


@dataclass(frozen=True)
class ContentItem:
    kind: str
    form: str
    meaning: str = ""
    evidence: str = ""
    metadata: dict = field(default_factory=dict)


def _clean(value: str) -> str:
    return (value or "").strip(" \t-*•")


def _kind_from_label(label: str) -> str:
    label = label.casefold()
    if label in {"root"}:
        return "root"
    if label in {"affix", "prefix", "suffix"}:
        return "affix"
    if label in {"grammar", "rule"}:
        return "rule"
    if label == "example":
        return "example"
    if label == "phrase":
        return "phrase"
    return "vocabulary"


def _mapping_item(line: str) -> ContentItem | None:
    match = _MAPPING.match(_BULLET.sub("", line, count=1))
    if not match:
        return None
    source = _clean(match.group("source"))
    target = _clean(match.group("target"))
    if not source or not target:
        return None

    label_match = _PAREN_LABEL.search(source)
    label = label_match.group("label") if label_match else ""
    if label_match:
        source = source[: label_match.start()].strip()
    return ContentItem(
        _kind_from_label(label) if label else "vocabulary",
        source,
        target,
        line,
        {"explicit": True, **({"label": label.casefold()} if label else {})},
    )


def _labeled_item(line: str) -> ContentItem | None:
    match = _LABEL.match(_BULLET.sub("", line, count=1))
    if not match:
        return None
    label = match.group("label").casefold()
    value = _clean(match.group("value"))
    if not value:
        return None

    # A labelled assertion can be either ``root: word = meaning`` or simply
    # ``grammar: ...``.  Preserve the original assertion as evidence.
    mapping = _MAPPING.match(value)
    if mapping and label in {"root", "affix", "prefix", "suffix", "word", "vocabulary", "meaning"}:
        return ContentItem(
            _kind_from_label(label),
            _clean(mapping.group("source")),
            _clean(mapping.group("target")),
            line,
            {"explicit": True, "label": label},
        )
    return ContentItem(
        _kind_from_label(label),
        value if label not in {"grammar", "rule"} else label,
        value,
        line,
        {"explicit": True, "label": label},
    )


def extract_explicit_items(text: str) -> list[ContentItem]:
    """Extract explicit MT assertions while preserving provenance.

    Plain prose is deliberately ignored.  No item returned here is by itself a
    claim that it should become MASTER; the authority policy is applied by the
    caller/store.
    """
    items: list[ContentItem] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        item = _labeled_item(line) or _mapping_item(line)
        if not item:
            continue
        key = (item.kind, item.form.casefold(), item.meaning.casefold())
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def summarize_content(text: str) -> dict:
    """Return a structured, deterministic summary suitable for persistence."""
    items = extract_explicit_items(text)
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item.kind, []).append(
            {"form": item.form, "meaning": item.meaning, "evidence": item.evidence, "metadata": item.metadata}
        )
    return {
        "item_count": len(items),
        "items": grouped,
        "vocabulary": grouped.get("vocabulary", []),
        "roots": grouped.get("root", []),
        "affixes": grouped.get("affix", []),
        "rules": grouped.get("rule", []),
        "examples": grouped.get("example", []),
        "phrases": grouped.get("phrase", []),
        "source_length": len(text or ""),
    }
