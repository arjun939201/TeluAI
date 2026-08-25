from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RouteDecision:
    mode: str
    intent: str
    language: str
    use_melimi: bool = False
    explicit: bool = False


def detect_language(text: str) -> str:
    value = text or ""
    telugu = len(re.findall(r"[\u0C00-\u0C7F]", value))
    latin = len(re.findall(r"[A-Za-z]", value))
    if telugu and latin:
        return "mixed"
    if telugu:
        return "telugu"
    words = re.findall(r"[A-Za-z]+", value.lower())
    roman_markers = {
        "ela", "em", "enti", "enduku", "ekkada", "evaru", "evvaru",
        "naaku", "naku", "mee", "mi", "mana", "manam", "unnav", "unnavu",
        "cheppu", "cheppandi", "ivvu", "ivvandi", "telusa", "teliyadu",
        "ante", "kosam", "lo", "ki", "tho", "ni", "ra", "bro", "anna",
        "akka", "baaga", "bagunnava", "bagunna", "ledu", "kavali", "chesi",
    }
    hits = sum(1 for word in words if word in roman_markers)
    return "roman_telugu" if hits >= 1 and hits >= max(1, len(words) // 5) else "english"


def _looks_coding(text: str) -> bool:
    value = text.lower()
    markers = (
        "python", "javascript", "typescript", "fastapi", "flask", "react",
        "sql", "api", "code", "coding", "debug", "bug", "function", "class ",
        "regex", "docker", "github", "program", "algorithm", "stack trace",
    )
    return any(marker in value for marker in markers) or "```" in text


def _looks_melimi(text: str) -> bool:
    value = text.lower()
    markers = (
        "మేలిమి", "మెలిమి", "melimi", "melimi telugu", "/word", "/content",
        "/learn", "/teach", "మార్చు మేలిమి", "మేలిమిలో", "మేలిమి పదం",
        "మేలిమి తెలుగు పదం", "మేలిమి equivalent", "melimi equivalent",
    )
    return any(marker in value for marker in markers)


def route_message(message: str, requested_mode: str = "auto") -> RouteDecision:
    text = (message or "").strip()
    language = detect_language(text)

    # Explicit user choice always wins. Standard Telugu is an opt-in mode;
    # everything else uses TeluAI's native Melimi language intelligence path.
    if requested_mode == "standard":
        return RouteDecision("standard", "conversation", language, False, True)
    if requested_mode == "melimi":
        return RouteDecision("melimi", "melimi", language, True, True)

    if text.startswith("/"):
        return RouteDecision("melimi", "language_command", language, True, True)

    if _looks_melimi(text):
        return RouteDecision("melimi", "melimi", language, True, False)

    # Telugu, Roman-Telugu, mixed input, English, and coding requests all enter
    # the native Melimi conversation path unless the user explicitly selected
    # Standard Telugu. This keeps the product language-centric while still
    # allowing the model to reason about arbitrary subjects.
    intent = "coding" if _looks_coding(text) else "conversation"
    return RouteDecision("melimi", intent, language, True, False)
