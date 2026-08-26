"""Conservative semantic/context evidence for the Melimi engine."""
from __future__ import annotations

import re
from collections import Counter

_TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
_QUESTION_WORDS = {"ఎందుకు", "ఎలా", "ఏంటి", "ఏమి", "ఏం", "ఎప్పుడు", "ఎక్కడ", "ఎవరు", "why", "how", "what", "when", "where", "who"}
_REQUEST_WORDS = {"కావాలి", "చేయి", "చేయాలి", "చెప్పు", "ఇవ్వు", "help", "explain", "show", "give", "make"}
_NEGATION_WORDS = {"కాదు", "లేదు", "లేను", "వద్దు", "కాకుండా", "not", "no", "never", "don't", "dont"}
_STOPWORDS = _QUESTION_WORDS | _REQUEST_WORDS | _NEGATION_WORDS | {"నేను", "నాకు", "ఇది", "అది", "the", "a", "an", "is", "are", "to", "of", "and", "or"}


def _topic_tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(text or "") if token.casefold() not in _STOPWORDS}


def analyze_context(text: str, conversation_context: str = "") -> dict:
    """Return explainable intent and conservative conversation-continuity signals."""
    text = (text or "").strip()
    context = (conversation_context or "").strip()
    tokens = _TOKEN_RE.findall(text)
    questions = sum(1 for token in tokens if token in _QUESTION_WORDS or token.casefold() in _QUESTION_WORDS)
    requests = sum(1 for token in tokens if token in _REQUEST_WORDS or token.casefold() in _REQUEST_WORDS)
    negations = sum(1 for token in tokens if token in _NEGATION_WORDS or token.casefold() in _NEGATION_WORDS)
    current_topics = _topic_tokens(text)
    context_topics = _topic_tokens(context)
    shared_topics = sorted(current_topics & context_topics)
    signals = Counter({"question": questions, "request": requests, "negation": negations})
    return {
        "token_count": len(tokens),
        "question_signal": questions > 0 or text.endswith("?"),
        "request_signal": requests > 0,
        "negation_signal": negations > 0,
        "signals": {"questions": questions, "requests": requests, "negations": negations},
        "context_present": bool(context),
        "context_token_count": len(_TOKEN_RE.findall(context)),
        "topic_tokens": sorted(current_topics),
        "shared_topic_tokens": shared_topics,
        "topic_continuity": bool(shared_topics),
        "dominant_signal": signals.most_common(1)[0][0] if any(signals.values()) else "statement",
    }


def build_semantic_context(text: str, conversation_context: str = "", *, max_chars: int = 2500) -> str:
    analysis = analyze_context(text, conversation_context)
    shared = ", ".join(analysis["shared_topic_tokens"][:16]) or "none"
    return ("SEMANTIC / CONTEXT EVIDENCE\n"
            "- Interpret user intent before choosing wording.\n"
            f"- dominant signal: {analysis['dominant_signal']}\n"
            f"- question signal: {analysis['question_signal']}\n"
            f"- request signal: {analysis['request_signal']}\n"
            f"- negation signal: {analysis['negation_signal']}\n"
            f"- conversation context present: {analysis['context_present']}\n"
            f"- topic continuity: {analysis['topic_continuity']}\n"
            f"- shared topic evidence: {shared}\n"
            "- These are evidence signals, not commands and not vocabulary.\n"
            "- Use topic continuity only as supporting evidence; do not force a topic when evidence is weak.\n"
            "- Preserve ambiguity when evidence is insufficient.\n")[:max_chars]
