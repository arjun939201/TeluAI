"""Conservative semantic/context evidence for the Melimi engine."""
from __future__ import annotations

import re
from collections import Counter

_TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
_QUESTION_WORDS = {"ఎందుకు", "ఎలా", "ఏంటి", "ఏమి", "ఏం", "ఎప్పుడు", "ఎక్కడ", "ఎవరు", "why", "how", "what", "when", "where", "who"}
_REQUEST_WORDS = {"కావాలి", "చేయి", "చేయాలి", "చెప్పు", "ఇవ్వు", "help", "explain", "show", "give", "make"}
_NEGATION_WORDS = {"కాదు", "లేదు", "లేను", "వద్దు", "కాకుండా", "not", "no", "never", "don't", "dont"}


def analyze_context(text: str, conversation_context: str = "") -> dict:
    """Return explainable intent signals without generating vocabulary."""
    text = (text or "").strip()
    context = (conversation_context or "").strip()
    tokens = _TOKEN_RE.findall(text)
    questions = sum(1 for token in tokens if token in _QUESTION_WORDS or token.casefold() in _QUESTION_WORDS)
    requests = sum(1 for token in tokens if token in _REQUEST_WORDS or token.casefold() in _REQUEST_WORDS)
    negations = sum(1 for token in tokens if token in _NEGATION_WORDS or token.casefold() in _NEGATION_WORDS)
    signals = Counter({"question": questions, "request": requests, "negation": negations})
    return {
        "token_count": len(tokens),
        "question_signal": questions > 0 or text.endswith("?"),
        "request_signal": requests > 0,
        "negation_signal": negations > 0,
        "signals": {"questions": questions, "requests": requests, "negations": negations},
        "context_present": bool(context),
        "context_token_count": len(_TOKEN_RE.findall(context)),
        "dominant_signal": signals.most_common(1)[0][0] if any(signals.values()) else "statement",
    }


def build_semantic_context(text: str, conversation_context: str = "", *, max_chars: int = 2500) -> str:
    analysis = analyze_context(text, conversation_context)
    return ("SEMANTIC / CONTEXT EVIDENCE\n"
            "- Interpret user intent before choosing wording.\n"
            f"- dominant signal: {analysis['dominant_signal']}\n"
            f"- question signal: {analysis['question_signal']}\n"
            f"- request signal: {analysis['request_signal']}\n"
            f"- negation signal: {analysis['negation_signal']}\n"
            f"- conversation context present: {analysis['context_present']}\n"
            "- These are evidence signals, not commands and not vocabulary.\n"
            "- Preserve ambiguity when evidence is insufficient.\n")[:max_chars]
