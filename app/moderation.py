"""Deterministic, evidence-first chat moderation primitives for TeluAI.

The classifier deliberately returns only policy decisions supported by visible
text/metadata. Screenshot OCR is kept separate so OCR uncertainty cannot become
an authoritative moderation decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


RULES = {
    "RULE_SPAM_SOLICITATION": ("LOW", "WARN"),
    "RULE_SEXUAL_EXPLICIT": ("HIGH", "MUTE"),
    "RULE_HARASSMENT_HATE": ("CRITICAL", "BAN"),
    "RULE_INAPPROPRIATE_NICKNAME_OR_MEDIA": ("MEDIUM", "REVIEW"),
}

# Deliberately compact high-signal patterns. Matching is boundary-aware and
# case-insensitive after transliteration normalization.
_SPAM = re.compile(r"(?:like\s*4\s*like|like\s*for\s*like|f\s*4\s*f|sub\s*4\s*sub|follow\s*4\s*follow|gift\s*exchange|https?://|www\.)", re.I)
_SEXUAL = re.compile(
    r"(?:sex\w*|porn\w*|nude\w*|naked|dick\b|cock\b|pussy\b|boob\w*|xxx\b|blowjob\w*|\bfuck\w*|\bsexy\b|"
    r"chud|lund|gaand|choot|randi|harami|madarchod|bhenchod|chodna|nangi|nanga|"
    r"kuss|zob|mitah|\bsex\b|\bsharmuta\b|\naked\b)", re.I,
)
_HARASSMENT = re.compile(
    r"(?:kill\s+you|i[' ]?ll\s+kill|death\s+threat|doxx(?:ing|ed)?|dox\s+you|"
    r"terrorist|go\s+die|\bidiot\b|\bstupid\b|\bretard\b|\bscum\b|\bslut\b|\bwhore\b|"
    r"hate\s+(?:all|every)\s+\w+|\bchinki\b|\bpaki\b)", re.I,
)

# Common metadata labels are treated as media/handle evidence rather than as
# chat text. This is intentionally conservative; generic names are not flagged.
_NSFW_HANDLE = re.compile(r"(?:porn|xxx|nude|sex|fuck|slut|whore|nsfw)", re.I)


def _normalize(text: str) -> str:
    value = text.casefold().replace("4", "a").replace("@", "a").replace("$", "s")
    value = re.sub(r"[^\w\s:/.-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _language(text: str) -> str:
    if re.search(r"[\u0590-\u05ff]", text):
        return "Hebrew"
    if re.search(r"[\u0600-\u06ff]", text):
        return "Arabic/Urdu"
    if re.search(r"[\u0900-\u097f]", text):
        return "Hindi"
    if re.search(r"[\u0c00-\u0c7f]", text):
        return "Telugu"
    # Latin text containing high-signal South Asian/Hebrew transliteration
    # vocabulary is labelled explicitly rather than pretending OCR identified
    # a script it did not see.
    lower = text.casefold()
    if re.search(r"\b(?:lund|gaand|choot|randi|harami|madarchod|bhenchod|chodna)\b", lower):
        return "Transliterated Hindi/Urdu"
    if re.search(r"\b(?:zob|mitah|sharmuta|kuss)\b", lower):
        return "Transliterated Hebrew/Arabic"
    return "English" if re.search(r"[a-z]", lower) else "Unknown"


@dataclass(frozen=True)
class ModerationViolation:
    username: str
    original_text: str
    detected_language: str
    translated_english_summary: str
    rule_id: str
    severity: str
    recommended_action: str
    justification: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _violation(username: str, text: str, rule: str, language: str, summary: str, reason: str) -> ModerationViolation:
    severity, action = RULES[rule]
    return ModerationViolation(username, text, language, summary, rule, severity, action, reason)


def moderate_text(username: str, text: str) -> list[ModerationViolation]:
    """Return high-signal violations for one visible chat message.

    Rules are evaluated independently so one message may legitimately trigger
    more than one policy category. Duplicate categories are collapsed.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    normalized = _normalize(text)
    language = _language(text)
    found: list[ModerationViolation] = []

    if _SPAM.search(normalized):
        found.append(_violation(username, text, "RULE_SPAM_SOLICITATION", language,
                                 "The message contains a link or reciprocal engagement solicitation.",
                                 "It matches a high-signal unsolicited link or mutual engagement request."))
    if _SEXUAL.search(normalized):
        found.append(_violation(username, text, "RULE_SEXUAL_EXPLICIT", language,
                                 "The message contains sexually explicit, suggestive, or vulgar language.",
                                 "It contains a high-signal sexual or vulgar expression covered by the explicit-content rule."))
    if _HARASSMENT.search(normalized):
        found.append(_violation(username, text, "RULE_HARASSMENT_HATE", language,
                                 "The message contains targeted abuse, hateful language, or a threat.",
                                 "It contains a targeted abusive, hateful, doxxing, or violent-threat expression."))
    return found


def moderate_screen_text(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Moderate OCR/transcribed screen messages while preserving exact text."""
    violations: list[ModerationViolation] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        username = str(item.get("username", "")).strip()
        text = str(item.get("text", ""))
        violations.extend(moderate_text(username, text))
        if username and _NSFW_HANDLE.search(username):
            violations.append(_violation(username, username, "RULE_INAPPROPRIATE_NICKNAME_OR_MEDIA",
                                          _language(username),
                                          "The displayed handle appears to contain NSFW terminology.",
                                          "The visible user handle contains a high-signal NSFW label and requires review."))
    payload = [v.as_dict() for v in violations]
    return {
        "screen_status": "VIOLATION_DETECTED" if payload else "CLEAN",
        "total_violations": len(payload),
        "violations": payload,
    }
