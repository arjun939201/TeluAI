"""Conservative sentence-level Melimi transformation helpers.

Transforms only Telugu tokens for which the shared MASTER root dictionary
provides a documented mapping. Unknown forms and non-Telugu text are preserved.
"""
from __future__ import annotations

import re
from typing import Any

from app.melimi.root_morphology import reduce_to_root, reapply_operations
from app.melimi.db_subject import language_roots, language_space_version

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+")


def transform_sentence(text: str) -> dict[str, Any]:
    source = str(text or "")
    roots = language_roots()
    trace: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        surface = match.group(0)
        form = reduce_to_root(surface, set(roots))
        if form.root not in roots:
            trace.append({"surface": surface, "root": form.root, "changed": False, "reason": "no_authoritative_root"})
            return surface
        target_root = roots[form.root]
        target = reapply_operations(target_root, form)
        changed = target != surface
        trace.append({
            "surface": surface,
            "root": form.root,
            "melimi_root": target_root,
            "operations": list(form.operations),
            "result": target,
            "changed": changed,
        })
        return target

    transformed = TOKEN_RE.sub(replace, source)
    return {
        "source": source,
        "text": transformed,
        "changed": transformed != source,
        "trace": trace,
        "language_space_version": language_space_version(),
    }
