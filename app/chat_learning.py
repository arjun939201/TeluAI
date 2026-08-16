"""Explicit Melimi teaching extracted from chat/content.

Ordinary conversation is never treated as language authority. Only explicit
teaching syntax is promoted immediately into the shared Language Space:

  చేవీనం - cellphone, mobile
  చేవీనం = cellphone
  చేవీనం - cellphone
  ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి
  (ప్రమాదకరమైన ప్రదేశాలు ఎన్నో మన ప్రపంచంలో ఉన్నాయి)

The last form stores the complete phrase and, when token alignment is safe,
reusable word mappings. This gives chat a controlled learning mechanism without
turning every user sentence into permanent language knowledge.
"""
from __future__ import annotations

import hashlib
import json
import re
from sqlalchemy import event, select
from sqlalchemy.orm import Session as SASession
from app.database import SessionLocal, MelimiRoot, MelimiExample, KnowledgeEntry, KnowledgeVersion, Message, now

_ARROW = re.compile(r"^\s*(.+?)\s*(?:→|->|=|–|-)\s*(.+?)\s*$")
_PAIR = re.compile(r"^\s*(.+?)\s*\(([^()]+)\)\s*$")
_PUNCT = ".,!?;:()[]{}\"'“”‘’"


def _tokens(text: str) -> list[str]:
    return [x.strip(_PUNCT) for x in text.split() if x.strip(_PUNCT)]


def _extract(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    roots: list[tuple[str, str]] = []
    phrases: list[tuple[str, str]] = []
    m = _ARROW.match(text)
    if m:
        left, right = m.group(1).strip(), m.group(2).strip()
        if len(left.split()) == 1 and len(right.split()) <= 8:
            roots.append((right, left))
        elif len(right.split()) == 1 and len(left.split()) <= 8:
            roots.append((left, right))
        else:
            phrases.append((left, right))

    p = _PAIR.match(text)
    if p:
        melimi_text, standard_text = p.group(1).strip(), p.group(2).strip()
        if melimi_text and standard_text:
            phrases.append((standard_text, melimi_text))
            mt, st = _tokens(melimi_text), _tokens(standard_text)
            if len(mt) == len(st) and 1 < len(mt) <= 20:
                for melimi, standard in zip(mt, st):
                    if melimi and standard and melimi != standard and len(melimi) <= 160 and len(standard) <= 160:
                        roots.append((standard, melimi))
    return roots, phrases


def _learn_in_session(db: SASession, message: str, user_id: int | None) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 20000:
        return False
    roots, phrases = _extract(text)
    if not roots and not phrases:
        return False

    source = f"chat_learning:user:{user_id or 'unknown'}"
    changed = False
    for standard, melimi in roots:
        row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == standard))
        target = melimi.split("/")[0].strip()
        if not target:
            continue
        if row:
            if row.melimi_root != target or row.status != "APPROVED":
                row.melimi_root = target; row.status = "APPROVED"; row.source = source; row.version += 1; row.updated_at = now(); changed = True
        else:
            db.add(MelimiRoot(standard_root=standard, melimi_root=target, status="APPROVED", source=source)); changed = True

    for standard_text, melimi_text in phrases:
        key = f"{standard_text[:220]} → {melimi_text[:220]}"
        if not db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "EXAMPLE") & (KnowledgeEntry.key == key))):
            db.add(KnowledgeEntry(kind="EXAMPLE", key=key, value=melimi_text,
                                  metadata_json=json.dumps({"standard": standard_text, "melimi": melimi_text, "source": "chat"}, ensure_ascii=False),
                                  status="MASTER", source=source)); changed = True
        if not db.scalar(select(MelimiExample).where((MelimiExample.standard_text == standard_text) & (MelimiExample.melimi_text == melimi_text))):
            db.add(MelimiExample(standard_text=standard_text, melimi_text=melimi_text, category="chat-learned", source=source, status="MASTER")); changed = True

    if changed:
        current = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        version = (current.version if current else 1) + 1
        db.add(KnowledgeVersion(version=version, source=source, checksum=hashlib.sha256(text.encode("utf-8")).hexdigest()))
    return changed


def learn_explicit_teaching(message: str, user_id: int | None = None) -> dict:
    """Synchronous helper for tests/admin tooling."""
    with SessionLocal() as db:
        changed = _learn_in_session(db, message, user_id)
        db.commit()
    if changed:
        reload_indexes()
    roots, phrases = _extract(message or "")
    return {"learned": changed, "roots": len(roots), "phrases": len(phrases)}


def reload_indexes() -> None:
    try:
        from app.melimi.root_morphology import reload_root_dictionary
        from app.melimi.registry import reload_registry
        from app.melimi.index import reload_index
        from app.melimi.firewall import reload_firewall
        reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
    except Exception:
        pass


def install_chat_learning() -> None:
    """Install a SQLAlchemy flush hook so saved user chat messages teach the space.

    It runs in the same DB transaction as the message, so knowledge and the
    message cannot drift apart. Only explicit mapping/translation syntax is
    recognized; ordinary chat is ignored.
    """
    SessionClass = SessionLocal.class_
    if getattr(SessionClass, "_teluai_chat_learning_installed", False):
        return

    @event.listens_for(SessionClass, "after_flush")
    def _after_flush(session, flush_context):
        for obj in list(session.new):
            if isinstance(obj, Message) and obj.role == "user":
                _learn_in_session(session, obj.content, obj.user_id)

    SessionClass._teluai_chat_learning_installed = True
