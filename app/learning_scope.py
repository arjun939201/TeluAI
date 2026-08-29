"""Scoped conversational Melimi learning.

Owner/admin chat teaches the shared global language space. Ordinary-user chat
is retained only in that user's private learning space. The table is separate
from authoritative master tables so conversational evidence cannot silently
become language authority.
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text

from app.database import engine

_TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
_MAPPING_RE = re.compile(r"(?<!\w)([^=→➜⇒\n]{1,100}?)(?:\s*=\s*|\s*(?:→|➜|⇒|->)\s*)([^=→➜⇒\n]{1,120})(?=$|[.!?;\n])")


def _init() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS melimi_chat_learning (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                scope TEXT NOT NULL,
                kind TEXT NOT NULL,
                standard TEXT NOT NULL DEFAULT '',
                melimi TEXT NOT NULL DEFAULT '',
                evidence TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_melimi_chat_learning_scope ON melimi_chat_learning(scope)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_melimi_chat_learning_standard ON melimi_chat_learning(standard)"))


def _scope(user_id: int, role: str) -> str:
    return "global" if str(role).lower() in {"owner", "admin"} else f"user:{int(user_id)}"


def _mapping_pairs(message: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in _MAPPING_RE.finditer(message or ""):
        left = match.group(1).strip(" \t.,:;()[]{}")
        right = match.group(2).strip(" \t.,:;()[]{}")
        if left and right and (left != right) and (len(left) <= 100 and len(right) <= 120):
            found.append((left, right))
    seen: set[tuple[str, str]] = set()
    return [pair for pair in found if not ((pair[0].casefold(), pair[1].casefold()) in seen or seen.add((pair[0].casefold(), pair[1].casefold())))]


def record_chat_learning(user_id: int, role: str, message: str) -> int:
    """Persist explicit Melimi suggestions from a chat in the correct scope.

    We only learn messages containing Telugu or an explicit Telugu mapping.
    Ordinary English/programming traffic is ignored. Global learning is never
    written into the authoritative MelimiRoot/KnowledgeEntry tables here.
    """
    text_value = str(message or "").strip()
    if not text_value or not (_TELUGU_RE.search(text_value) or _mapping_pairs(text_value)):
        return 0
    _init()
    scope = _scope(user_id, role)
    pairs = _mapping_pairs(text_value)
    rows: list[tuple[str, str, str]] = [("vocabulary", a, b) for a, b in pairs]
    if not rows:
        # Keep useful Telugu grammar/usage evidence, but do not treat it as a
        # lexical authority. It is evidence that can be used in future chat.
        if "=" in text_value or "→" in text_value or "->" in text_value:
            return 0
        rows.append(("observation", "", text_value[:50000]))
    with engine.begin() as conn:
        for kind, standard, melimi in rows:
            conn.execute(text("""
                INSERT INTO melimi_chat_learning
                    (id, user_id, scope, kind, standard, melimi, evidence, metadata)
                VALUES
                    (:id, :user_id, :scope, :kind, :standard, :melimi, :evidence, :metadata)
            """), {
                "id": _next_id(conn), "user_id": user_id, "scope": scope,
                "kind": kind, "standard": standard, "melimi": melimi,
                "evidence": text_value[:50000],
                "metadata": json.dumps({"authority": "global_trusted_chat" if scope == "global" else "private_user_chat", "role": role}, ensure_ascii=False),
            })
    return len(rows)


def _next_id(conn) -> int:
    value = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM melimi_chat_learning")).scalar_one()
    return int(value)


def search_learning(query: str, user_id: int, limit: int = 8) -> list[dict[str, Any]]:
    """Return global learning plus only the requesting user's private learning."""
    _init()
    terms = [x for x in re.split(r"\s+", str(query or "").strip()) if len(x) >= 2][:12]
    if not terms:
        return []
    scopes = ["global", f"user:{int(user_id)}"]
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, user_id, scope, kind, standard, melimi, evidence, metadata
            FROM melimi_chat_learning
            WHERE scope IN (:global_scope, :user_scope)
            ORDER BY id DESC
            LIMIT 1000
        """), {"global_scope": scopes[0], "user_scope": scopes[1]}).mappings().all()
    hits = []
    for row in rows:
        hay = " ".join([row["standard"], row["melimi"], row["evidence"]]).casefold()
        score = sum(1 for term in terms if term.casefold() in hay)
        if score:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item.get("metadata") or "{}")
            except Exception:
                item["metadata"] = {}
            item["_score"] = score
            hits.append(item)
    hits.sort(key=lambda x: (x["_score"], x["scope"] == "global", x["id"]), reverse=True)
    return hits[:max(1, min(int(limit), 20))]


def exact_mapping(word: str, user_id: int) -> str | None:
    """Resolve a taught mapping from global or this user's private scope only."""
    _init()
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT standard, melimi, scope FROM melimi_chat_learning
            WHERE kind='vocabulary' AND standard=:word
              AND scope IN ('global', :user_scope)
            ORDER BY CASE WHEN scope='global' THEN 0 ELSE 1 END, id DESC
            LIMIT 1
        """), {"word": word, "user_scope": f"user:{int(user_id)}"}).mappings().all()
    return str(rows[0]["melimi"]).strip() if rows else None
