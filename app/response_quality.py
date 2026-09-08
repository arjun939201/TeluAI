"""Deterministic response-quality guards for TeluAI output."""
from __future__ import annotations

import re

from app.melimi.registry import standard_to_melimi

_STAR_BULLET = re.compile(r"(?m)^\s*\*\s+")
_STAR_EMPHASIS = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def clean_chat_formatting(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = _STAR_BULLET.sub("", value)
    value = _STAR_EMPHASIS.sub(r"\1", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def repair_confirmed_melimi_terms(text: str) -> str:
    value = str(text or "")
    for source in ("ఇతర", "ఉపయోగించడం"):
        preferred = standard_to_melimi(source)
        if not preferred:
            continue
        value = re.sub(
            rf"(?<![\u0C00-\u0C7F]){re.escape(source)}(?![\u0C00-\u0C7F])",
            preferred,
            value,
        )
    return value


def validate_melimi_response(text: str) -> dict[str, object]:
    original = str(text or "")
    formatted = clean_chat_formatting(original)
    repaired = repair_confirmed_melimi_terms(formatted)
    return {
        "valid": repaired == original,
        "changed": repaired != original,
        "text": repaired,
        "issues": [
            issue
            for issue in (
                "star_formatting" if formatted != original else None,
                "mixed_melimi_term" if repaired != formatted else None,
            )
            if issue
        ],
    }
