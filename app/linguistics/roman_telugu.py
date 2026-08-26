"""Structured Roman-Telugu linguistic evidence for downstream Melimi routing.

This module deliberately separates lexical evidence from unknown input. It does
not guess meanings for unknown Roman-Telugu words.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .normalizer import ROMAN_TELUGU, normalize_roman_telugu, tokenize

_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*|[\u0C00-\u0C7F]+|\d+")


def analyze_roman_telugu(text: str) -> Dict:
    """Return structured evidence without promoting guesses to language facts."""
    raw = str(text or "").strip()
    normalized = normalize_roman_telugu(raw)
    roman_words = [w.lower() for w in re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", raw)]
    known = [w for w in roman_words if w in ROMAN_TELUGU]
    unknown = [w for w in roman_words if w not in ROMAN_TELUGU]
    telugu_tokens = [w for w in tokenize(normalized) if re.search(r"[\u0C00-\u0C7F]", w)]
    confidence = len(known) / len(roman_words) if roman_words else 0.0
    return {
        "raw": raw,
        "normalized": normalized,
        "roman_tokens": roman_words,
        "known_tokens": known,
        "unknown_tokens": unknown,
        "known_count": len(known),
        "unknown_count": len(unknown),
        "confidence": confidence,
        "has_telugu_output": bool(telugu_tokens),
        "mixed_input": bool(re.search(r"[A-Za-z]", raw) and re.search(r"[\u0C00-\u0C7F]", raw)),
    }
