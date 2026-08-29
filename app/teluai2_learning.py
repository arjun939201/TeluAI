"""Safe, user-scoped language learning extracted from ordinary chat.

A user's explicit suggestion can be remembered immediately for that user's future
conversations. It does not become global Melimi authority. Global authority
still requires the existing review/governance path.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.database import SessionLocal, UserMemory, now
from sqlalchemy import select


TELUGU = r"[\u0C00-\u0C7F]"
WORD = rf"{TELUGU}+(?:{TELUGU}+)*"


@dataclass(frozen=True)
class LearningSuggestion:
    kind: str
    key: str
    value: str
    source: str


def _clean(value: str) -> str:
    return " ".join(value.strip().split()).strip(" .,:;!?\"'()[]{}")


def extract_suggestion(text: str) -> LearningSuggestion | None:
    """Recognize explicit natural-language teaching, not arbitrary conversation."""
    text = _clean(text)
    if not text:
        return None

    patterns = [
        rf"^(?P<standard>{WORD})\s*(?:=|అంటే|అనగా)\s*(?P<melimi>{WORD})$",
        rf"^(?:మేలిమి(?:\s*తెలుగు)?(?:లో)?|మెలిమి(?:\s*తెలుగు)?(?:లో)?)\s*(?P<standard>{WORD})\s*(?:అంటే|అనగా|కి|కు)\s*(?P<melimi>{WORD})$",
        rf"^(?P<standard>{WORD})\s*(?:మేలిమి(?:\s*తెలుగు)?(?:లో)?|మెలిమి(?:\s*తెలుగు)?(?:లో)?)\s*(?:అంటే|అనగా|అంటారు|అనాలి)\s*(?P<melimi>{WORD})$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.UNICODE)
        if match:
            standard = _clean(match.group("standard"))
            melimi = _clean(match.group("melimi"))
            if standard and melimi and standard != melimi:
                return LearningSuggestion("VOCABULARY", standard, melimi, text)

    # Grammar suggestions must be explicitly marked; ordinary Telugu discussion
    # is never silently promoted to a language rule.
    grammar_match = re.match(
        r"^(?:మేలిమి|మెలిమి)\s*(?:తెలుగు\s*)?(?:వ్యాకరణ|నియమం)\s*[:：-]\s*(.+)$",
        text,
        flags=re.UNICODE,
    )
    if grammar_match:
        rule = _clean(grammar_match.group(1))
        if len(rule) >= 4:
            return LearningSuggestion("GRAMMAR", "rule", rule, text)
    return None


def remember_suggestion(user_id: int, suggestion: LearningSuggestion) -> bool:
    """Upsert one user-scoped learning item; never modifies global authority."""
    key = f"melimi_chat:{suggestion.kind}:{suggestion.key}"
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


def learned_for_user(user_id: int, limit: int = 20) -> list[dict[str, str]]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(UserMemory)
            .where((UserMemory.user_id == user_id) & UserMemory.key.like("melimi_chat:%"))
            .order_by(UserMemory.created_at.desc())
            .limit(max(1, min(limit, 50)))
        ).all()
    result = []
    for row in rows:
        try:
            item = json.loads(row.value)
            if isinstance(item, dict) and item.get("kind") and item.get("value"):
                result.append(item)
        except (TypeError, json.JSONDecodeError):
            continue
    return result


def prompt_context(user_id: int) -> str:
    items = learned_for_user(user_id)
    if not items:
        return ""
    lines = ["USER-SUGGESTED MELIMI KNOWLEDGE (personal, not global authority):"]
    for item in reversed(items):
        if item["kind"] == "VOCABULARY":
            lines.append(f"- vocabulary: {item['key']} → {item['value']}")
        else:
            lines.append(f"- grammar suggestion: {item['value']}")
    lines.append("Use these suggestions when relevant, but do not call them globally authoritative unless the authoritative language database confirms them.")
    return "\n".join(lines)
