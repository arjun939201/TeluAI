"""Explicit Melimi teaching extracted from chat/content.

Only unambiguous teaching syntax is learned automatically. Ordinary conversation
is never treated as language authority. Supported forms include:

  చేవీనం - cellphone, mobile
  చేవీనం = cellphone
  Melimi phrase (standard phrase)

For sentence pairs in parentheses, aligned tokens are stored as reusable lexical
knowledge when both sides have the same token count. The complete phrase is also
stored as a MASTER example, preserving context and grammar.
"""
from __future__ import annotations

import json
import re
import hashlib
from app.database import SessionLocal, MelimiRoot, MelimiExample, KnowledgeEntry, KnowledgeVersion, now

_ARROW = re.compile(r"^\s*(.+?)\s*(?:→|->|=|–|-)\s*(.+?)\s*$")
_PAIR = re.compile(r"^\s*(.+?)\s*\(([^()]+)\)\s*$")


def _tokens(text: str) -> list[str]:
    return [x.strip(".,!?;:()[]{}\"'“”‘’") for x in text.split() if x.strip(".,!?;:()[]{}\"'“”‘’")]


def _upsert_root(db, standard: str, melimi: str, source: str, category: str = "chat-learned") -> bool:
    standard, melimi = standard.strip(), melimi.strip()
    if not standard or not melimi or len(standard) > 160 or len(melimi) > 160:
        return False
    row = db.scalar(__import__("sqlalchemy").select(MelimiRoot).where(MelimiRoot.standard_root == standard))
    if row:
        row.melimi_root = melimi.split("/")[0].strip()
        row.status = "APPROVED"
        row.source = source
        row.version += 1
        row.updated_at = now()
    else:
        db.add(MelimiRoot(standard_root=standard, melimi_root=melimi.split("/")[0].strip(), status="APPROVED", source=source))
    return True


def learn_explicit_teaching(message: str, user_id: int | None = None) -> dict:
    """Learn only explicit language-teaching material from one chat message.

    Returns counts and the original teaching source. This is deliberately
    conservative: a normal sentence such as "నాకు మొబైల్ ఉంది" does nothing.
    """
    text = (message or "").strip()
    if not text or len(text) > 20000:
        return {"learned": False, "roots": 0, "phrases": 0, "reason": "not_teaching"}

    roots: list[tuple[str, str]] = []
    phrases: list[tuple[str, str]] = []

    # Explicit mapping: standard -> Melimi or Melimi -> standard. We interpret
    # Telugu-script left/right context conservatively; a phrase with a space is
    # stored as an example rather than a root.
    m = _ARROW.match(text)
    if m:
        left, right = m.group(1).strip(), m.group(2).strip()
        if len(left.split()) == 1 and len(right.split()) <= 8:
            # Existing convention in TeluAI uses source_root -> melimi_root.
            roots.append((right, left))
        elif len(right.split()) == 1 and len(left.split()) <= 8:
            roots.append((left, right))
        else:
            phrases.append((left, right))

    # Explicit example: Melimi sentence (standard Telugu sentence).
    pair = _PAIR.match(text)
    if pair:
        melimi_text, standard_text = pair.group(1).strip(), pair.group(2).strip()
        if melimi_text and standard_text:
            phrases.append((standard_text, melimi_text))
            mt, st = _tokens(melimi_text), _tokens(standard_text)
            if len(mt) == len(st) and 1 < len(mt) <= 20:
                for melimi, standard in zip(mt, st):
                    # Ignore punctuation-only pieces and identical words; they
                    # provide no new lexical information.
                    if melimi and standard and melimi != standard and len(melimi) <= 160 and len(standard) <= 160:
                        roots.append((standard, melimi))

    if not roots and not phrases:
        return {"learned": False, "roots": 0, "phrases": 0, "reason": "not_explicit_teaching"}

    source = f"chat_learning:user:{user_id or 'unknown'}"
    learned_roots = 0
    with SessionLocal() as db:
        for standard, melimi in roots:
            if _upsert_root(db, standard, melimi, source):
                learned_roots += 1

        for standard_text, melimi_text in phrases:
            key = f"{standard_text[:220]} → {melimi_text[:220]}"
            existing = db.scalar(__import__("sqlalchemy").select(KnowledgeEntry).where((KnowledgeEntry.kind == "EXAMPLE") & (KnowledgeEntry.key == key)))
            if not existing:
                db.add(KnowledgeEntry(kind="EXAMPLE", key=key, value=melimi_text, metadata_json=json.dumps({"standard": standard_text, "melimi": melimi_text, "source": "chat"}, ensure_ascii=False), status="MASTER", source=source))

        for standard_text, melimi_text in phrases:
            existing = db.scalar(__import__("sqlalchemy").select(MelimiExample).where((MelimiExample.standard_text == standard_text) & (MelimiExample.melimi_text == melimi_text)))
            if not existing:
                db.add(MelimiExample(standard_text=standard_text, melimi_text=melimi_text, category="chat-learned", source=source, status="MASTER"))

        current = db.scalars(__import__("sqlalchemy").select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        version = (current.version if current else 1) + 1
        db.add(KnowledgeVersion(version=version, source=source, checksum=hashlib.sha256(text.encode("utf-8")).hexdigest()))
        db.commit()

    # Reload in-process indexes immediately. Failure here must not roll back
    # durable PostgreSQL/SQLite knowledge; the next request can reload them.
    try:
        from app.melimi.root_morphology import reload_root_dictionary
        from app.melimi.registry import reload_registry
        from app.melimi.index import reload_index
        from app.melimi.firewall import reload_firewall
        reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
    except Exception:
        pass

    return {"learned": True, "roots": learned_roots, "phrases": len(phrases), "source": source}
