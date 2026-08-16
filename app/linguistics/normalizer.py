import re
from typing import Dict, List

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*|\d+")

# Conservative common Roman-Telugu hints. This is not the language model.
ROMAN_TELUGU = {
    "hi": "హాయ్", "hello": "హలో", "hey": "హే",
    "haa": "హా", "haaa": "హా", "avunu": "అవును",
    "sare": "సరే", "ok": "ఓకే", "okay": "ఓకే",
    "cheppu": "చెప్పు", "em": "ఏం", "enti": "ఏంటి",
    "emiti": "ఏమిటి", "emle": "ఏంలేదు", "emledu": "ఏంలేదు",
    "emledhu": "ఏంలేదు", "nenu": "నేను", "nuvvu": "నువ్వు",
    "nuvu": "నువ్వు", "meeru": "మీరు", "ela": "ఎలా",
    "inka": "ఇంకా", "ledu": "లేదు", "ledhu": "లేదు",
    "baaunna": "బాగున్నా", "baagunna": "బాగున్నా",
    "baaunnanu": "బాగున్నాను", "baagunnanu": "బాగున్నాను",
    "thanks": "ధన్యవాదాలు", "thankyou": "ధన్యవాదాలు",
    "thank you": "ధన్యవాదాలు",
    "cinemas": "సినిమాలు", "cinema": "సినిమా",
    "gurinchi": "గురించి",
}


def normalize_roman_telugu(text: str) -> str:
    """Normalize conservative Roman-Telugu hints even in mixed-script input."""
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return ""
    for source in sorted(ROMAN_TELUGU, key=len, reverse=True):
        value = re.sub(
            r"(?<![A-Za-z])" + re.escape(source) + r"(?![A-Za-z])",
            ROMAN_TELUGU[source],
            value,
            flags=re.I,
        )
    return value


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text or "")


def analyze_input(text: str) -> Dict:
    raw = str(text or "").strip()
    normalized = normalize_roman_telugu(raw)
    toks = tokenize(normalized)
    return {
        "raw": raw,
        "normalized_hint": normalized,
        "tokens": toks,
        "has_telugu_script": bool(TELUGU_RE.search(raw)),
        "short": len(toks) <= 3,
        "mixed_script": bool(TELUGU_RE.search(raw)) and bool(re.search(r"[A-Za-z]", raw)),
    }
