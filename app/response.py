from __future__ import annotations

import re

from app.melimi.firewall import deterministic_repair
from app.texl_translation_intent import TranslationMode, classify_translation_intent

_INTERNAL_MARKERS = (
    "system prompt",
    "system instructions",
    "internal instructions",
    "developer message",
    "developer instructions",
    "hidden prompt",
    "chain of thought",
)


def _repair_lexical_answer(answer: str, source_message: str) -> str:
    """Prevent source-case leakage for explicit lexical-equivalence questions.

    This is deliberately conservative: only a known authoritative Melimi
    mapping is considered, and only the common Telugu accusative surfaces of
    the learned Melimi equivalent are normalized back to its canonical form.
    It never creates a mapping or changes grammatical translations.
    """
    intent = classify_translation_intent(source_message)
    if intent.mode is not TranslationMode.LEXICAL_EQUIVALENT:
        return answer

    # Ask the existing authoritative firewall for registered source mappings.
    # It supplies the source -> canonical Melimi vocabulary without creating
    # a second vocabulary table here.
    lex = __import__("app.melimi.firewall", fromlist=["subject_lexicon"]).subject_lexicon()
    preferred = lex.get("preferred", {})
    if not preferred:
        return answer

    # If the answer contains an inflected form of an authoritative Melimi word,
    # normalize only the explicit lexical-question result. This is intentionally
    # limited to the Telugu accusative endings relevant to the contract.
    for melimi in set(preferred.values()):
        if not melimi:
            continue
        for ending in ("ను", "ని"):
            surface = melimi + ending
            answer = re.sub(rf"(?<![\u0C00-\u0C7F]){re.escape(surface)}(?![\u0C00-\u0C7F])", melimi, answer)
    return answer


def clean_response(text: str, source_message: str = "") -> str:
    """Apply deterministic, low-risk output hygiene before persistence/display."""
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

    value = deterministic_repair(value)
    value = _repair_lexical_answer(value, source_message)
    return re.sub(r"\n{3,}", "\n\n", value).strip()
