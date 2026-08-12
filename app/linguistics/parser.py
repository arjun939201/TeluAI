
import re
from typing import Dict, List

from app.linguistics.normalizer import tokenize, normalize_roman_telugu


QUESTION_WORDS = {
    "ఏంటి": "what",
    "ఏమిటి": "what",
    "ఏం": "what",
    "ఎందుకు": "why",
    "ఎందుక": "why",
    "ఎలా": "how",
    "ఎక్కడ": "where",
    "ఎప్పుడు": "when",
    "ఎవరు": "who",
    "ఎవరూ": "who",
    "ఎంత": "how_much",
    "ఎన్ని": "how_many",
}


def detect_sentence_force(text: str) -> str:
    value = normalize_roman_telugu(text).strip().lower()
    if "?" in value or "？" in value:
        return "question"
    if any(value.startswith(x) for x in ("చెప్పు", "చూడి", "వెళ్ళు", "రా", "వెళ్ళండి")):
        return "request_or_command"
    if any(x in value for x in ("లేదా", "కానీ", "అయితే")):
        return "statement_with_relation"
    return "statement_or_fragment"


def detect_question_type(text: str) -> str:
    value = normalize_roman_telugu(text)
    for word, kind in QUESTION_WORDS.items():
        if word in value:
            return kind
    return "unknown"


def extract_linguistic_hints(text: str) -> Dict:
    normalized = normalize_roman_telugu(text)
    toks = tokenize(normalized)
    return {
        "normalized": normalized,
        "token_count": len(toks),
        "sentence_force": detect_sentence_force(text),
        "question_type": detect_question_type(text),
        "tokens": toks,
        "negation_hint": any(x in normalized for x in ("లేదు", "కాదు", "వద్దు", "లేను", "లేవు")),
        "first_person_hint": any(x in normalized for x in ("నేను", "నాకు", "నా")),
        "second_person_hint": any(x in normalized for x in ("నువ్వు", "నీకు", "నీ")),
    }


# Common Telugu case/postposition clitics (vibhakti) and the plural marker.
# Telugu is agglutinative: these attach directly to a word with no space,
# so exact-string vocabulary lookups miss every inflected form unless the
# clitic is stripped first. This list is intentionally conservative (real
# vibhakti/postposition endings only) to avoid mis-stripping unrelated words.
CASE_SUFFIXES = sorted({
    "లతో", "లలో", "లకు", "లను", "లని", "లపై", "నుంచి", "నుండి",
    "యొక్క", "వరకు", "వైపు", "తోపాటు", "మీదుగా",
    "తో", "లో", "లు", "ను", "ని", "కు", "కి", "గా", "లా",
    "పై", "మీద", "కింద", "కోసం", "వల్ల", "చేత", "వద్ద", "మధ్య", "గురించి",
}, key=len, reverse=True)


def analyze_word_surface(word: str) -> Dict:
    # Lightweight morphological clues. It deliberately avoids claiming
    # a full grammatical parse when evidence is insufficient.
    for suffix in CASE_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return {
                "surface": word,
                "base_candidate": word[:-len(suffix)],
                "case_or_suffix_hint": suffix,
            }
    return {"surface": word, "base_candidate": word, "case_or_suffix_hint": None}


def case_variants(word: str) -> List[str]:
    """Return the surface form plus any case/plural-stripped base form(s).

    Used to match an inflected word (e.g. with -లో/-కు/-లు attached) back to
    its uninflected vocabulary entry, so registered/loan-word status applies
    strictly across grammatical cases and variations, not only bare forms.
    """
    word = (word or "").strip()
    if not word:
        return []
    variants = [word]
    surface = word
    # Peel iteratively: a word can carry more than one clitic, e.g. plural + case.
    for _ in range(2):
        hint = analyze_word_surface(surface)
        base = hint["base_candidate"]
        if base == surface:
            break
        variants.append(base)
        surface = base
    seen = []
    for v in variants:
        if v not in seen:
            seen.append(v)
    return seen
