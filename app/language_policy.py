"""Runtime language policy for TeluAI.

Melimi is a first-class output variety, not a word-replacement mode. Input may
be standard Telugu, mixed-language Telugu, Roman Telugu, Melimi, or another
language. Explicit user requests override the default Melimi output target.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LanguageVariety(str, Enum):
    STANDARD_TELUGU = "standard_telugu"
    MIXED_TELUGU = "mixed_telugu"
    ROMAN_TELUGU = "roman_telugu"
    MELIMI_TELUGU = "melimi_telugu"
    ENGLISH = "english"
    OTHER = "other"


@dataclass(frozen=True)
class LanguageDecision:
    input_variety: LanguageVariety
    output_variety: LanguageVariety
    explicit_output: bool


def detect_input_variety(message: str) -> LanguageVariety:
    """Conservative lightweight detection; semantic understanding remains LLM/TEX-L work."""
    text = str(message or "")
    telugu = sum("\u0c00" <= ch <= "\u0c7f" for ch in text)
    latin = sum(ch.isascii() and ch.isalpha() for ch in text)
    if telugu and latin:
        return LanguageVariety.MIXED_TELUGU
    if telugu:
        return LanguageVariety.STANDARD_TELUGU
    if latin and any(token in text.lower().split() for token in ("cheppu", "enti", "emiti", "ela", "enduku", "naku", "meeru")):
        return LanguageVariety.ROMAN_TELUGU
    if latin:
        return LanguageVariety.ENGLISH
    return LanguageVariety.OTHER


def choose_output_variety(message: str) -> LanguageDecision:
    """Choose output: explicit language requests win; otherwise Melimi is default."""
    text = str(message or "").lower()
    explicit = (
        ("english" in text and any(x in text for x in ("in english", "english lo", "english lo cheppu", "english lo ivvu")))
        or ("తెలుగు" in str(message) and any(x in str(message) for x in ("సాధారణ తెలుగులో", "ప్రామాణిక తెలుగులో")))
        or any(x in text for x in ("in standard telugu", "standard telugu lo", "in roman telugu"))
    )
    if explicit:
        if "english" in text:
            output = LanguageVariety.ENGLISH
        elif "roman telugu" in text:
            output = LanguageVariety.ROMAN_TELUGU
        else:
            output = LanguageVariety.STANDARD_TELUGU
    else:
        output = LanguageVariety.MELIMI_TELUGU
    return LanguageDecision(detect_input_variety(message), output, explicit)
