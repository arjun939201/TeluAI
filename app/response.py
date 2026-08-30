from __future__ import annotations

import re

from app.melimi.firewall import deterministic_repair


_INTERNAL_MARKERS = (
    "system prompt",
    "system instructions",
    "internal instructions",
    "developer message",
    "developer instructions",
    "hidden prompt",
    "chain of thought",
)


def clean_response(text: str) -> str:
    """Apply deterministic, low-risk output hygiene before persistence/display.

    Formatting cleanup is followed by the existing authoritative Melimi firewall.
    The firewall only rewrites registered/source-backed lexical mappings; it does
    not invent vocabulary. Internal-instruction markers are removed only when
    they appear as explicit leakage, rather than using an LLM judge on every
    response.
    """
    value = str(text or "").strip()
    value = re.sub(r"^\s*(assistant|teluai)\s*:\s*", "", value, flags=re.I)
    value = re.sub(r"\n{3,}", "\n\n", value)

    lowered = value.casefold()
    if any(marker in lowered for marker in _INTERNAL_MARKERS):
        lines = []
        for line in value.splitlines():
            line_lower = line.casefold()
            if any(marker in line_lower for marker in _INTERNAL_MARKERS):
                continue
            lines.append(line)
        value = "\n".join(lines).strip()

    # Reuse the authoritative deterministic Melimi layer instead of maintaining
    # a second response-time vocabulary or replacement table here.
    value = deterministic_repair(value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()
