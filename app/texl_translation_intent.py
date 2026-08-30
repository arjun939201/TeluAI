"""Conservative translation-intent classification for TEX-L.

A lexical-equivalence question asks what a word is called in Melimi. Its
surface case ending must not be copied into the lexical answer. A sentence
translation, however, must preserve the grammatical role of the source term.

This module classifies intent only; it does not invent morphology or perform
translation itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TranslationMode(str, Enum):
    LEXICAL_EQUIVALENT = "lexical_equivalent"
    GRAMMATICAL_TRANSLATION = "grammatical_translation"
    GENERAL = "general"


@dataclass(frozen=True)
class TranslationIntent:
    mode: TranslationMode
    preserve_source_surface_role: bool
    reason: str


_LEXICAL_QUESTION_MARKERS = (
    "ఏమంటారు",
    "ఏమని అంటారు",
    "ఏమని పిలుస్తారు",
    "ఎలా అంటారు",
    "ఇలా అంటారా",
)
_TRANSLATION_MARKERS = (
    "అనువదించు",
    "అనువాదం",
    "తర్జుమా",
    "translate",
    "translation",
)


def classify_translation_intent(message: str) -> TranslationIntent:
    text = str(message or "").strip()
    lowered = text.lower()

    # "...మెలిమి తెలుగులో ఏమంటారు?" is a lexical-equivalence request even
    # when the queried source token itself carries an accusative ending.
    if any(marker in text for marker in _LEXICAL_QUESTION_MARKERS):
        return TranslationIntent(
            TranslationMode.LEXICAL_EQUIVALENT,
            False,
            "the user asks for the name/equivalent of a term",
        )

    if any(marker in lowered for marker in _TRANSLATION_MARKERS):
        return TranslationIntent(
            TranslationMode.GRAMMATICAL_TRANSLATION,
            True,
            "the user explicitly requests translation",
        )

    return TranslationIntent(
        TranslationMode.GENERAL,
        True,
        "no explicit lexical-equivalence request detected",
    )
