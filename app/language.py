import re
from typing import List

ROMAN_TELUGU_MAP = {
    "emle": "ఏంలేదు", "emledu": "ఏంలేదు", "emledhu": "ఏంలేదు",
    "em ledu": "ఏంలేదు", "em ledhu": "ఏంలేదు",
    "baaunnanu": "బాగున్నాను", "baagunnanu": "బాగున్నాను",
    "baagunna": "బాగున్నా", "bagunna": "బాగున్నా",
    "nuvvu": "నువ్వు", "nuvu": "నువ్వు",
    "cheppu": "చెప్పు", "sare": "సరే", "haa": "హా", "haaa": "హా",
    "avunu": "అవును", "kaadu": "కాదు", "kadu": "కాదు",
    "enti": "ఏంటి", "em": "ఏం", "nenu": "నేను", "meeru": "మీరు",
    "ela": "ఎలా", "inka": "ఇంకా", "ledu": "లేదు", "ledhu": "లేదు",
    "thanks": "ధన్యవాదాలు", "thankyou": "ధన్యవాదాలు",
    "thank you": "ధన్యవాదాలు",
}

INTENT_HINTS = {
    "hi": "greeting", "hello": "greeting", "hey": "greeting",
    "నమస్కారం": "greeting", "టేంకణములు": "greeting",
    "haa": "acknowledgement", "హా": "acknowledgement",
    "avunu": "agreement", "అవును": "agreement",
    "sare": "agreement", "సరే": "agreement",
    "cheppu": "request_to_continue", "చెప్పు": "request_to_continue",
    "emle": "nothing_or_negative", "ఏంలేదు": "nothing_or_negative",
    "ela": "asking_how", "ఎలా": "asking_how",
    "thanks": "gratitude", "ధన్యవాదాలు": "gratitude",
}


def normalize_roman_telugu(text: str) -> str:
    """Return a Telugu-script hint for common Roman-Telugu input.

    This is deliberately conservative: if Telugu script is already present,
    the original text is returned unchanged.
    """
    text = str(text or "").strip()
    if not text:
        return ""

    lowered = re.sub(r"\s+", " ", text.lower())
    if re.search(r"[\u0C00-\u0C7F]", lowered):
        return text

    result = lowered
    for source in sorted(ROMAN_TELUGU_MAP, key=len, reverse=True):
        result = re.sub(
            r"(?<![a-z])" + re.escape(source) + r"(?![a-z])",
            ROMAN_TELUGU_MAP[source],
            result,
            flags=re.IGNORECASE,
        )
    return result


def detect_intents(text: str) -> List[str]:
    normalized = normalize_roman_telugu(text)
    tokens = set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z]+", normalized.lower()))
    return list(dict.fromkeys(
        INTENT_HINTS[token] for token in tokens if token in INTENT_HINTS
    ))


def build_language_context(raw_text: str) -> str:
    normalized = normalize_roman_telugu(raw_text)
    intents = detect_intents(raw_text)

    return "\n".join([
        "LOCAL LANGUAGE ANALYSIS:",
        f"- raw input: {raw_text.strip()}",
        f"- normalized Telugu hint: {normalized}",
        f"- likely intent: {', '.join(intents) if intents else 'infer from context'}",
        "- This analysis is only a hint.",
        "- Preserve the user's actual meaning, wording intent, and conversational tone.",
    ])
