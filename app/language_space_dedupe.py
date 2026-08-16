"""Defensive deduplication for the unified Language Space view.

Different authoritative tables can legitimately contain the same linguistic
record (for example a dictionary root and a mirrored KnowledgeEntry). The
admin UI should present one canonical card while retaining provenance counts.
This module wraps the existing list_space function without changing database
records or deleting provenance.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from app import language_space as _space


_DICTIONARY_KINDS = {"DICTIONARY", "MELIMI_MAPPING", "ROOT", "VOCABULARY"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _canonical_kind(value: Any) -> str:
    kind = str(value or "").strip().upper()
    return "DICTIONARY" if kind in _DICTIONARY_KINDS else kind


def _canonical_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _canonical_kind(entry.get("kind")),
        _norm(entry.get("key")),
        _norm(entry.get("value")),
    )


def _merge(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: "OrderedDict[tuple[str, str, str], dict[str, Any]]" = OrderedDict()
    for item in items:
        key = _canonical_key(item)
        current = merged.get(key)
        if current is None:
            current = dict(item)
            current["source_count"] = 1
            current["sources"] = [item.get("source")] if item.get("source") else []
            if _canonical_kind(item.get("kind")) == "DICTIONARY":
                current["kind"] = "DICTIONARY"
            merged[key] = current
            continue

        current["source_count"] = int(current.get("source_count", 1)) + 1
        source = item.get("source")
        if source and source not in current["sources"]:
            current["sources"].append(source)
        current["version"] = max(int(current.get("version", 1)), int(item.get("version", 1)))
        # Prefer a real database id over a virtual source id when duplicates
        # represent the same linguistic record.
        if int(current.get("id", 0)) < 0 <= int(item.get("id", 0)):
            current["id"] = item["id"]
        current["editable"] = bool(current.get("editable", True) and item.get("editable", True))
    return list(merged.values())


_original_list_space = _space.list_space


def list_space(kind: str | None = None, q: str | None = None, limit: int = 100):
    # Fetch a wider candidate window first so duplicates do not consume the
    # user's visible result limit. The underlying function still enforces its
    # own hard cap, while this wrapper enforces the requested final limit.
    candidates = _original_list_space(kind=kind, q=q, limit=500)
    unique = _merge(candidates)
    return unique[: max(1, min(int(limit), 500))]


_space.list_space = list_space
