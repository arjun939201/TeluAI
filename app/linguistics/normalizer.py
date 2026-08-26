import re
from typing import Dict, List

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*|\d+")

ROMAN_TELUGU = {
    "hi": "హాయ్", "hello": "హలో", "hey": "హే", "haa": "హా", "haaa": "హా",
    "avunu": "అవును", "sare": "సరే", "ok": "ఓకే", "okay": "ఓకే",
    "cheppu": "చెప్పు", "cheppandi": "చెప్పండి", "em": "ఏం", "enti": "ఏంటి",
    "emiti": "ఏమిటి", "emle": "ఏంలేదు", "emledu": "ఏంలేదు", "emledhu": "ఏంలేదు",
    "nenu": "నేను", "naaku": "నాకు", "naku": "నాకు", "naa": "నా", "nuvvu": "నువ్వు",
    "nuvu": "నువ్వు", "meeru": "మీరు", "mee": "మీ", "ela": "ఎలా", "enduku": "ఎందుకు",
    "ekkada": "ఎక్కడ", "evaru": "ఎవరు", "evvaru": "ఎవరు", "inka": "ఇంకా", "ledu": "లేదు",
    "ledhu": "లేదు", "kavali": "కావాలి", "chesi": "చేసి", "chey": "చేయి", "ivvu": "ఇవ్వు",
    "ivvandi": "ఇవ్వండి", "telusa": "తెలుసా", "teliyadu": "తెలియదు", "ante": "అంటే",
    "kosam": "కోసం", "tho": "తో", "ni": "ని", "ki": "కి", "lo": "లో", "ra": "రా",
    "anna": "అన్నా", "akka": "అక్కా", "bro": "బ్రో", "baaunna": "బాగున్నా", "baagunna": "బాగున్నా",
    "baaunnanu": "బాగున్నాను", "baagunnanu": "బాగున్నాను", "bagunnava": "బాగున్నావా",
    "thanks": "ధన్యవాదాలు", "thankyou": "ధన్యవాదాలు", "thank you": "ధన్యవాదాలు",
    "cinemas": "సినిమాలు", "cinema": "సినిమా", "gurinchi": "గురించి",
}


def normalize_roman_telugu(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return ""
    for source in sorted(ROMAN_TELUGU, key=len, reverse=True):
        value = re.sub(r"(?<![A-Za-z])" + re.escape(source) + r"(?![A-Za-z])", ROMAN_TELUGU[source], value, flags=re.I)
    return value


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text or "")


def analyze_input(text: str) -> Dict:
    raw = str(text or "").strip()
    normalized = normalize_roman_telugu(raw)
    toks = tokenize(normalized)
    roman_tokens = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", raw.lower())
    normalized_roman = sum(1 for token in roman_tokens if token in ROMAN_TELUGU)
    has_telugu = bool(TELUGU_RE.search(raw))
    has_latin = bool(re.search(r"[A-Za-z]", raw))
    return {
        "raw": raw,
        "normalized_hint": normalized,
        "tokens": toks,
        "has_telugu_script": has_telugu,
        "has_latin_script": has_latin,
        "roman_telugu_token_count": normalized_roman,
        "roman_telugu_confidence": min(1.0, normalized_roman / max(1, len(roman_tokens))) if roman_tokens else 0.0,
        "short": len(toks) <= 3,
        "mixed_script": has_telugu and has_latin,
    }
