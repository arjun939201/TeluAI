"""Structured Roman-Telugu linguistic evidence for downstream Melimi routing."""

from __future__ import annotations

import re
from typing import Dict

from .normalizer import ROMAN_TELUGU, normalize_roman_telugu, tokenize


def analyze_roman_telugu(text: str) -> Dict:
    """Separate known lexical evidence from unknown input without guessing."""
    raw = str(text or "").strip()
    normalized = normalize_roman_telugu(raw)
    roman_tokens = [w.lower() for w in re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", raw)]
    known_tokens = [w for w in roman_tokens if w in ROMAN_TELUGU]
    unknown_tokens = [w for w in roman_tokens if w not in ROMAN_TELUGU]
    confidence = len(known_tokens) / len(roman_tokens) if roman_tokens else 0.0
    return {
        "raw": raw,
        "normalized": normalized,
        "tokens": tokenize(normalized),
        "roman_tokens": roman_tokens,
        "known_tokens": known_tokens,
        "unknown_tokens": unknown_tokens,
        "known_count": len(known_tokens),
        "unknown_count": len(unknown_tokens),
        "confidence": confidence,
        "has_telugu_output": bool(re.search(r"[\u0C00-\u0C7F]", normalized)),
        "mixed_input": bool(re.search(r"[A-Za-z]", raw) and re.search(r"[\u0C00-\u0C7F]", raw)),
    }
