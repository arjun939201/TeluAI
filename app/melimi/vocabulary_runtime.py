"""Runtime Melimi vocabulary layer.

This is a deterministic language component, not a prompt trick.  It applies
only established lexical mappings after an answer has been produced, while
preserving punctuation and unknown words.  The layer is intentionally small
and extensible so authoritative vocabulary can later be loaded from the
Melimi language store without changing the chat pipeline.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


# Seed vocabulary requested for the TeluAI runtime contract.
# Multiple meanings are accepted as input forms; the first/primary Melimi
# form is emitted.
_SEED_VOCABULARY: dict[str, dict[str, Any]] = {
    "టేంకణం": {
        "meanings": ("నమస్కారం", "hello", "hi"),
        "type": "greeting",
    },
    "హాళికాను": {
        "meanings": ("ఆసక్తికరం", "ఆసక్తికరమైన", "interesting"),
        "type": "adjective",
    },
    "ఎడాటం": {
        "meanings": ("విషయం", "subject", "matter"),
        "type": "noun",
    },
}

_PUNCTUATION = ",.!?;:\u0964\u0965。！？、"


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


@lru_cache(maxsize=1)
def _mapping() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for melimi, data in _SEED_VOCABULARY.items():
        for meaning in data.get("meanings", ()):
            mapping[_norm(meaning)] = melimi
    return mapping


def _split_word(token: str) -> tuple[str, str]:
    """Separate trailing punctuation while keeping the original token intact."""
    if not token:
        return "", ""
    trailing = ""
    while token and token[-1] in _PUNCTUATION:
        trailing = token[-1] + trailing
        token = token[:-1]
    return token, trailing


def convert_text(text: str) -> str:
    """Convert established Standard/English lexical equivalents to Melimi.

    Unknown words are returned unchanged.  This makes the component safe to
    place after the normal AI response generation step.
    """
    if not text:
        return text

    mapping = _mapping()
    output: list[str] = []
    for token in text.split():
        clean, punctuation = _split_word(token)
        replacement = mapping.get(_norm(clean))
        output.append((replacement if replacement else token) + (punctuation if replacement else ""))
    return " ".join(output)


def vocabulary_snapshot() -> dict[str, dict[str, Any]]:
    """Return a read-only-friendly snapshot for diagnostics/tests."""
    return {
        word: {"meanings": list(data["meanings"]), "type": data["type"]}
        for word, data in _SEED_VOCABULARY.items()
    }
