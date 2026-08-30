"""First-class language-variety policy for TeluAI.

This module defines the language contract without inventing Melimi vocabulary or
grammar. It separates input understanding from output selection so Melimi can
become the default generation target while standard/mixed Telugu remains fully
understandable and explicit user requests take precedence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LanguageVariety(str, Enum):
    MELIMI = "melimi"
    STANDARD_TELUGU = "standard_telugu"
    MIXED_TELUGU = "mixed_telugu"
    ROMAN_TELUGU = "roman_telugu"
    ENGLISH = "english"
    OTHER = "other"


@dataclass(frozen=True)
class LanguageDecision:
    input_variety: LanguageVariety
    output_variety: LanguageVariety
    explicit_output_request: bool


def normalize_output_request(request: str | None) -> LanguageVariety | None:
    """Resolve only explicit, unambiguous output requests."""
    value = " ".join(str(request or "").strip().casefold().split())
    if not value:
        return None
    aliases = {
        "melimi": LanguageVariety.MELIMI,
        "melimi telugu": LanguageVariety.MELIMI,
        "మేలిమి తెలుగు": LanguageVariety.MELIMI,
        "మెలిమి తెలుగు": LanguageVariety.MELIMI,
        "standard telugu": LanguageVariety.STANDARD_TELUGU,
        "తెలుగు": LanguageVariety.STANDARD_TELUGU,
        "సాధారణ తెలుగు": LanguageVariety.STANDARD_TELUGU,
        "mixed telugu": LanguageVariety.MIXED_TELUGU,
        "roman telugu": LanguageVariety.ROMAN_TELUGU,
        "english": LanguageVariety.ENGLISH,
        "ఇంగ్లీష్": LanguageVariety.ENGLISH,
    }
    return aliases.get(value)


def choose_output_variety(explicit_request: str | None) -> LanguageVariety:
    """Explicit user request wins; otherwise Melimi is the product default."""
    return normalize_output_request(explicit_request) or LanguageVariety.MELIMI


def language_contract() -> str:
    """Compact generation contract for the LLM context."""
    return """భాషా విధానం:
- వినియోగదారు తెలుగు, రోమన్ తెలుగు, ఇంగ్లీష్ లేదా కలగలిసిన భాషలో రాసినా భావాన్ని అర్థం చేసుకో.
- స్పష్టమైన భాషా అభ్యర్థన ఉంటే ఆ భాష/రూపంలోనే సమాధానం ఇవ్వు.
- స్పష్టమైన అభ్యర్థన లేకపోతే మేలిమి తెలుగును ప్రధాన సమాధాన భాషగా ఉపయోగించు.
- మేలిమి పదం లేదా వ్యాకరణ రూపం అధికారికంగా నేర్చుకోనప్పుడు కల్పించవద్దు.
- ప్రామాణిక తెలుగు పదాన్ని మేలిమి పదంతో మార్చడం కేవలం అర్థం, సందర్భం, నేర్చుకున్న అధికారిక జ్ఞానం మద్దతు ఇచ్చినప్పుడు మాత్రమే చేయాలి.
- మేలిమిని కేవలం పదాల మార్పిడిగా కాకుండా స్వతంత్ర భాషా రూపంగా అర్థం చేసుకుని రూపొందించాలి.
"""
