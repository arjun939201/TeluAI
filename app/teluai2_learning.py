"""Personal Telugu language learning extracted from explicit chat suggestions.

Only clear user suggestions/corrections are learned. Ordinary conversation is
never promoted to language knowledge. Learned items are scoped to the user and
are automatically available in later conversations for that same user.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select

from app.database import SessionLocal, UserMemory, now

TELUGU = r"[\u0C00-\u0C7F]"
WORD = rf"{TELUGU}+(?:{TELUGU}+)*"


@dataclass(frozen=True)
class LearningSuggestion:
    kind: str
    key: str
    value: str
    source: str


def _clean(value: str) -> str:
    return " ".join(str(value).strip().split()).strip(" .,:;!?\"'()[]{}")


def extract_suggestions(text: str) -> list[LearningSuggestion]:
    """Extract only explicit Telugu vocabulary/grammar teaching from chat."""
    text = str(text or "").strip()
    if not text:
        return []

    found: list[LearningSuggestion] = []
    patterns = [
        rf"(?P<standard>{WORD})\s*(?:=|అంటే|అనగా)\s*(?P<telugu>{WORD})",
        rf"(?P<standard>{WORD})\s*(?:కి|కు)?\s*బదులు\s*(?P<telugu>{WORD})\s*(?:వాడాలి|వాడండి|చెప్పాలి|అనాలి)",
        rf"(?:మేలిమి|మెలిమి)(?:\s*తెలుగు)?(?:లో)?\s*(?P<standard>{WORD})\s*(?:అంటే|అనగా|అంటారు|అనాలి)\s*(?P<telugu>{WORD})",
        rf"(?P<standard>{WORD})\s*(?:ను|ని)?\s*(?:మేలిమి|మెలిమి)(?:\s*తెలుగు)?(?:లో)?\s*(?:గా|లో)?\s*(?:<|=|అంటే|అనగా)\s*(?P<telugu>{WORD})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.UNICODE):
            standard = _clean(match.group("standard"))
            target = _clean(match.group("telugu"))
            if standard and target and standard != target:
                candidate = LearningSuggestion("VOCABULARY", standard, target, _clean(match.group(0)))
                if candidate not in found:
                    found.append(candidate)

    grammar_patterns = [
        r"(?:మేలిమి|మెలిమి)(?:\s*తెలుగు)?\s*(?:వ్యాకరణ|నియమం)\s*[:：-]\s*(.+)",
        r"(?:వ్యాకరణంగా|వ్యాకరణంలో)\s*(.+?)\s*(?:అని|అలా)?\s*(?:వాడాలి|చెప్పాలి|ఉంటుంది)[.]?$",
        r"(?:ఇక్కడ|ఈ సందర్భంలో)\s*(.+?)\s*(?:వాడాలి|చెప్పాలి)\s*(?:అని|\.|$)",
    ]
    for pattern in grammar_patterns:
        match = re.search(pattern, text, flags=re.UNICODE)
        if match:
            rule = _clean(match.group(1))
            if len(rule) >= 4:
                candidate = LearningSuggestion("GRAMMAR", "rule", rule, _clean(match.group(0)))
                if candidate not in found:
                    found.append(candidate)
                break
    return found


def extract_suggestion(text: str) -> LearningSuggestion | None:
    """Backward-compatible single-suggestion helper."""
    suggestions = extract_suggestions(text)
    return suggestions[0] if suggestions else None


def remember_suggestion(user_id: int, suggestion: LearningSuggestion) -> bool:
    key = f"telugu_chat_learning:{suggestion.kind}:{suggestion.key}"
    payload = json.dumps(
        {"kind": suggestion.kind, "key": suggestion.key, "value": suggestion.value, "source": suggestion.source},
        ensure_ascii=False,
    )
    with SessionLocal() as db:
        row = db.scalar(select(UserMemory).where((UserMemory.user_id == user_id) & (UserMemory.key == key)))
        if row:
            row.value = payload
        else:
            db.add(UserMemory(user_id=user_id, key=key, value=payload, created_at=now()))
        db.commit()
    return True


def learned_for_user(user_id: int, limit: int = 40) -> list[dict[str, str]]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(UserMemory)
            .where((UserMemory.user_id == user_id) & UserMemory.key.like("telugu_chat_learning:%"))
            .order_by(UserMemory.created_at.desc())
            .limit(max(1, min(limit, 100)))
        ).all()
    result: list[dict[str, str]] = []
    for row in rows:
        try:
            item = json.loads(row.value)
            if isinstance(item, dict) and item.get("kind") and item.get("value"):
                result.append({str(k): str(v) for k, v in item.items()})
        except (TypeError, json.JSONDecodeError):
            continue
    return result


def prompt_context(user_id: int) -> str:
    items = learned_for_user(user_id)
    if not items:
        return ""
    lines = ["ఈ వినియోగదారు గత సంభాషణల్లో స్పష్టంగా సూచించిన వ్యక్తిగత తెలుగు భాషా జ్ఞాపకాలు:"]
    for item in reversed(items):
        if item.get("kind") == "VOCABULARY":
            lines.append(f"- పద వినియోగ సూచన: {item.get('key', '')} → {item.get('value', '')}")
        elif item.get("kind") == "GRAMMAR":
            lines.append(f"- వ్యాకరణ సూచన: {item.get('value', '')}")
    lines.append("ఇవి ఈ వినియోగదారుడి వ్యక్తిగత సూచనలు. సంబంధిత సందర్భంలో సహజంగా ఉపయోగించు; సూచనను ప్రస్తావించాల్సిన అవసరం లేకపోతే ప్రస్తావించవద్దు.")
    return "\n".join(lines)
