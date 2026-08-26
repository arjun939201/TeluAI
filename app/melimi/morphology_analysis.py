"""Conservative structured analysis of documented Melimi morphology."""
from __future__ import annotations

from typing import Dict, List, Optional

from app.melimi.formation_rules import PREFIXES, SUFFIXES, explain_element


def _markers(word: str, table: Dict, *, suffix: bool) -> List[dict]:
    value = (word or "").strip()
    found: List[dict] = []
    for element in sorted(table, key=len, reverse=True):
        matched = value.endswith(element) if suffix else value.startswith(element)
        if matched:
            evidence = explain_element(element)
            found.append({"element": element, "kind": "suffix" if suffix else "prefix", "known": evidence["known"], "formations": evidence["formations"]})
    return found


def analyze_morphology(word: str) -> dict:
    """Return only corpus-backed morphological evidence for a surface word."""
    value = (word or "").strip()
    if not value:
        return {"word": "", "known": False, "status": "EMPTY", "prefixes": [], "suffixes": [], "evidence": []}
    prefixes = _markers(value, PREFIXES, suffix=False)
    suffixes = _markers(value, SUFFIXES, suffix=True)
    evidence = prefixes + suffixes
    return {"word": value, "known": bool(evidence), "status": "DOCUMENTED" if evidence else "UNKNOWN", "prefixes": prefixes, "suffixes": suffixes, "evidence": evidence}


def documented_elements(word: str) -> List[str]:
    """Return documented formation elements detected on the surface."""
    return [item["element"] for item in analyze_morphology(word)["evidence"]]


def explain_morphology(word: str) -> Optional[dict]:
    """Return structured evidence, or None when the surface has no marker."""
    analysis = analyze_morphology(word)
    return analysis if analysis["known"] else None
