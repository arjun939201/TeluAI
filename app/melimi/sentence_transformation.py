"""Conservative sentence-level Melimi transformation.

This layer composes the existing root-first morphology engine with structured
per-token evidence. It never performs raw substring replacement and leaves
unsupported or ambiguous tokens unchanged.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.melimi.root_morphology import MorphologicalForm, load_root_dictionary, reduce_to_root, reapply_operations

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")


def _transform_token(token: str, roots: Dict[str, str]) -> dict:
    form: MorphologicalForm = reduce_to_root(token, roots)
    if form.root not in roots:
        return {
            "surface": token,
            "root": form.root,
            "operations": list(form.operations),
            "transformed": token,
            "changed": False,
            "status": "UNRESOLVED",
        }

    target_root = roots[form.root]
    transformed = reapply_operations(target_root, form)
    changed = transformed != token
    return {
        "surface": token,
        "root": form.root,
        "target_root": target_root,
        "operations": list(form.operations),
        "transformed": transformed,
        "changed": changed,
        "status": "TRANSFORMED" if changed else "UNCHANGED",
    }


def transform_sentence(text: str, *, roots: Optional[Dict[str, str]] = None) -> dict:
    """Transform supported Telugu sentence constituents into Melimi.

    Punctuation, whitespace, Latin text, and unresolved tokens are preserved.
    The result includes an auditable trace so downstream systems can validate
    that every change came from an authoritative root and known operation.
    """
    value = text or ""
    root_map = roots if roots is not None else load_root_dictionary()
    trace: List[dict] = []

    def replace(match: re.Match) -> str:
        record = _transform_token(match.group(0), root_map)
        trace.append(record)
        return record["transformed"]

    transformed = TOKEN_RE.sub(replace, value)
    changed = [item for item in trace if item["changed"]]
    unresolved = [item["surface"] for item in trace if item["status"] == "UNRESOLVED"]

    return {
        "source": value,
        "transformed": transformed,
        "changed": bool(changed),
        "trace": trace,
        "changed_tokens": len(changed),
        "unresolved_tokens": unresolved,
        "safe": all(item["status"] != "UNRESOLVED" or not item["operations"] for item in trace),
    }


def validate_transformation(result: dict) -> dict:
    """Validate that each changed token has an authoritative target root."""
    violations: List[str] = []
    for item in result.get("trace", []):
        if item.get("changed") and not item.get("target_root"):
            violations.append(f"missing target root: {item.get('surface', '')}")
        if item.get("status") == "UNRESOLVED" and item.get("operations"):
            violations.append(f"unsupported transformation: {item.get('surface', '')}")
    return {"valid": not violations, "violations": violations}
