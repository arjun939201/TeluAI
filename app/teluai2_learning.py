"""Scoped Telugu language learning extracted from explicit chat suggestions.

Learning has two scopes:
- owner / approved active admin suggestions -> shared global memory
- ordinary user suggestions -> private memory for that user

Neither scope silently becomes the authoritative master language corpus.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select, text

from app.database import SessionLocal, UserMemory, engine, now

TELUGU = r"[\u0C00-\u0C7F]"
WORD = rf"{TELUGU}+(?:{TELUGU}+)*"
GLOBAL_TABLE = "teluai_global_learning"


@dataclass(frozen=True)
class LearningSuggestion:
    kind: str
    key: str
    value: str
    source: str


def _ensure_global_table() -> None:
    with engine.begin() as db:
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {GLOBAL_TABLE} (
                id INTEGER PRIMARY KEY,
                kind VARCHAR(30) NOT NULL,
                learning_key VARCHAR(255) NOT NULL,
                learning_value TEXT NOT NULL,
                source VARCHAR(120) NOT NULL,
                source_user_id INTEGER NOT NULL,
                evidence TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kind, learning_key)
            )
        """))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{GLOBAL_TABLE}_key ON {GLOBAL_TABLE}(learning_key)"))


def _is_global_role(role: str) -> bool:
    # `admin` is the approved administrator role in the authenticated account
    # model; inactive accounts cannot reach the authenticated chat boundary.
    return str(role or "").strip().lower() in {"owner", "admin"}


def _clean(value: str) -> str:
    return " ".join(str(value).strip().split()).strip(" .,:;!?\"'()[]{}")


def extract_suggestions(text: str) -> list[LearningSuggestion]:
    """Extract only clear, explicit Telugu vocabulary/grammar teaching."""
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
    return (extract_suggestions(text) or [None])[0]


def remember_suggestion(user_id: int, suggestion: LearningSuggestion, role: str = "user") -> bool:
    """Persist an explicit suggestion in its correct trust scope."""
    if _is_global_role(role):
        _ensure_global_table()
        with engine.begin() as db:
            db.execute(text(f"""
                INSERT INTO {GLOBAL_TABLE}
                    (id, kind, learning_key, learning_value, source, source_user_id, evidence)
                VALUES
                    (:id, :kind, :learning_key, :learning_value, :source, :source_user_id, :evidence)
                ON CONFLICT(kind, learning_key) DO UPDATE SET
                    learning_value=excluded.learning_value,
                    source=excluded.source,
                    source_user_id=excluded.source_user_id,
                    evidence=excluded.evidence,
                    updated_at=CURRENT_TIMESTAMP
            """), {
                "id": _next_global_id(db), "kind": suggestion.kind,
                "learning_key": suggestion.key, "learning_value": suggestion.value,
                "source": "owner_chat" if str(role).lower() == "owner" else "approved_admin_chat",
                "source_user_id": int(user_id), "evidence": suggestion.source[:50000],
            })
        return True

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


def _next_global_id(db) -> int:
    return int(db.execute(text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {GLOBAL_TABLE}")).scalar_one())


def learned_global(limit: int = 80) -> list[dict[str, str]]:
    """Return shared owner/admin learning, never ordinary-user learning."""
    _ensure_global_table()
    with engine.begin() as db:
        rows = db.execute(text(f"""
            SELECT kind, learning_key, learning_value, source
            FROM {GLOBAL_TABLE}
            ORDER BY updated_at DESC, id DESC
            LIMIT :limit
        """), {"limit": max(1, min(int(limit), 200))}).mappings().all()
    return [
        {"kind": str(row["kind"]), "key": str(row["learning_key"]), "value": str(row["learning_value"]), "source": str(row["source"])}
        for row in rows
    ]


def learned_for_user(user_id: int, limit: int = 40) -> list[dict[str, str]]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(UserMemory)
            .where((UserMemory.user_id == user_id) & (UserMemory.key.like("telugu_chat_learning:%")))
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


def prompt_context(user_id: int, role: str = "user") -> str:
    """Build model context from global trusted chat learning + private memory."""
    global_items = learned_global()
    private_items = learned_for_user(user_id)
    if not global_items and not private_items:
        return ""

    lines: list[str] = []
    if global_items:
        lines.append("సిస్టమ్ యొక్క భాగస్వామ్య తెలుగు భాషా జ్ఞాపకం (యజమాని/ఆమోదిత నిర్వాహకుల స్పష్టమైన సూచనల నుంచి):")
        for item in reversed(global_items):
            if item.get("kind") == "VOCABULARY":
                lines.append(f"- పద వినియోగ సూచన: {item.get('key', '')} → {item.get('value', '')}")
            elif item.get("kind") == "GRAMMAR":
                lines.append(f"- వ్యాకరణ సూచన: {item.get('value', '')}")
        lines.append("ఈ భాగస్వామ్య జ్ఞాపకం అన్ని వినియోగదారులకు సందర్భానుసారం ఉపయోగించవచ్చు; తెలియని విషయాన్ని దీనితో కలిపి ఊహించవద్దు.")

    if private_items:
        lines.append("ఈ వినియోగదారు గత సంభాషణల్లో స్పష్టంగా సూచించిన వ్యక్తిగత తెలుగు భాషా జ్ఞాపకాలు:")
        for item in reversed(private_items):
            if item.get("kind") == "VOCABULARY":
                lines.append(f"- పద వినియోగ సూచన: {item.get('key', '')} → {item.get('value', '')}")
            elif item.get("kind") == "GRAMMAR":
                lines.append(f"- వ్యాకరణ సూచన: {item.get('value', '')}")
        lines.append("ఇవి ఈ వినియోగదారుడి వ్యక్తిగత సూచనలు. ఇతర వినియోగదారులకు వర్తింపజేయవద్దు.")
    return "\n".join(lines)
