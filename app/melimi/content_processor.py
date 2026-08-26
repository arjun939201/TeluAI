"""Structured Melimi content ingestion helpers.

This module classifies explicit language material without promoting model
observations to authoritative MT. It is intentionally deterministic and
keeps the source text intact for provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

_MAPPING = re.compile(r"^\s*(?P<source>[^=→]+?)\s*(?:=|→|->)\s*(?P<target>.+?)\s*$")
_HEADING = re.compile(r"^\s*(?:#{1,6}\s*)?(?P<name>[^:]{1,80})\s*:\s*(?P<value>.+?)\s*$")


@dataclass(frozen=True)
class ContentItem:
    kind: str
    form: str
    meaning: str = ""
    evidence: str = ""
    metadata: dict = field(default_factory=dict)


def extract_explicit_items(text: str) -> list[ContentItem]:
    """Extract only explicit, human-written MT assertions from content."""
    items: list[ContentItem] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        mapping = _MAPPING.match(line)
        if mapping:
            source = mapping.group("source").strip(" -*\t")
            target = mapping.group("target").strip()
            if source and target:
                items.append(ContentItem("vocabulary", source, target, line, {"explicit": True}))
                continue
        heading = _HEADING.match(line)
        if heading:
            name = heading.group("name").strip()
            value = heading.group("value").strip()
            low = name.casefold()
            if any(key in low for key in ("root", "affix", "suffix", "prefix", "grammar", "rule", "meaning")):
                kind = "rule" if any(key in low for key in ("grammar", "rule")) else "language_metadata"
                items.append(ContentItem(kind, name, value, line, {"explicit": True}))
    return items


def summarize_content(text: str) -> dict:
    """Return a deterministic structured summary suitable for persistence."""
    items = extract_explicit_items(text)
    return {
        "item_count": len(items),
        "vocabulary": [
            {"form": i.form, "meaning": i.meaning, "evidence": i.evidence, "metadata": i.metadata}
            for i in items if i.kind == "vocabulary"
        ],
        "rules": [
            {"form": i.form, "meaning": i.meaning, "evidence": i.evidence, "metadata": i.metadata}
            for i in items if i.kind == "rule"
        ],
        "metadata": [
            {"form": i.form, "meaning": i.meaning, "evidence": i.evidence, "metadata": i.metadata}
            for i in items if i.kind == "language_metadata"
        ],
        "source_length": len(text or ""),
    }
