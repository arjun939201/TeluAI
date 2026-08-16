"""Explicit /word and /content language commands.

Normal chat is never promoted to Language Space. The request layer decides
whether the authenticated actor is allowed to make an immediate MASTER change;
regular-user contributions are routed to the learning candidate workflow.
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import select

from app.database import KnowledgeEntry, KnowledgeVersion, MelimiExample, MelimiRoot, SessionLocal, now

_COMMAND_RE = re.compile(r"^\s*/(?P<kind>word|content)\b(?P<body>.*?)\s*$", re.I | re.S)
_MAPPING_RE = re.compile(r"^\s*(?P<source>.+?)\s*(?:=|→|->)\s*(?P<melimi>.+?)\s*$", re.S)


def parse_command(message: str):
    match = _COMMAND_RE.match(message or "")
    if not match:
        return None
    kind = match.group("kind").lower()
    body = match.group("body").strip()
    if kind == "word":
        parsed = _MAPPING_RE.match(body)
        if not parsed:
            raise ValueError("Usage: /word source-word = melimi-word")
        source = parsed.group("source").strip()
        melimi = parsed.group("melimi").strip()
        if not source or not melimi or len(source) > 160 or len(melimi) > 160:
            raise ValueError("Word entries must be 160 characters or less per side.")
        return kind, {"source": source, "melimi": melimi}
    if not body:
        raise ValueError("Content cannot be empty.")
    note = re.match(r"^(.*?)(?:\s*\(([^()]*)\))?\s*$", body, re.S)
    content = (note.group(1) or "").strip()
    meaning = (note.group(2) or "").strip()
    if not content:
        raise ValueError("Content cannot be empty.")
    if len(content) > 50000:
        raise ValueError("Content is too large. Maximum is 50,000 characters.")
    return kind, {"content": content, "meaning": meaning}


def learn_explicit_teaching(message: str, user_id: int | None = None):
    """Apply an explicit command directly to MASTER data.

    The API only calls this function for admin/owner actors. Regular users are
    routed through ``app.learning.service`` so the authority boundary remains
    server-side rather than being a UI convention.
    """
    parsed = parse_command(message)
    if not parsed:
        return {"learned": False, "changed": False, "roots": 0, "phrases": 0}
    kind, payload = parsed
    source = f"chat_command:user:{user_id or 'unknown'}"
    changed = False
    roots = phrases = 0
    with SessionLocal() as db:
        if kind == "word":
            standard, melimi = payload["source"].strip(), payload["melimi"].strip()
            melimi_root = melimi.split("/")[0].strip()
            row = None
            for candidate in db.scalars(select(MelimiRoot)).all():
                if str(candidate.standard_root or "").strip().casefold() == standard.casefold():
                    row = candidate
                    break
            if row:
                if row.melimi_root != melimi_root or row.status != "MASTER" or row.source != source:
                    row.standard_root = standard; row.melimi_root = melimi_root; row.status = "MASTER"; row.source = source; row.version += 1; row.updated_at = now(); changed = True
            else:
                db.add(MelimiRoot(standard_root=standard, melimi_root=melimi_root, status="MASTER", source=source)); changed = True

            record = None
            for item in db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.kind.in_(["VOCABULARY", "ROOT"]))).all():
                try:
                    metadata = json.loads(item.metadata_json or "{}")
                except (TypeError, ValueError):
                    metadata = {}
                if str(metadata.get("standard", "")).strip().casefold() == standard.casefold():
                    record = item
                    break
            metadata = {"standard": standard, "melimi": melimi, "source": "chat-command"}
            encoded = json.dumps(metadata, ensure_ascii=False)
            if record:
                if record.value != melimi or record.metadata_json != encoded or record.status != "MASTER":
                    record.kind = "VOCABULARY"; record.key = f"word:{standard.casefold()}"; record.value = melimi; record.metadata_json = encoded; record.status = "MASTER"; record.source = source; record.version += 1; changed = True
            else:
                db.add(KnowledgeEntry(kind="VOCABULARY", key=f"word:{standard.casefold()}", value=melimi, metadata_json=encoded, status="MASTER", source=source)); changed = True
            roots = 1
        else:
            content, meaning = payload["content"], payload["meaning"]
            key = f"chat:{hashlib.sha256((content + '\n' + meaning).encode()).hexdigest()}"
            record = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "CONTENT") & (KnowledgeEntry.key == key)))
            if not record:
                db.add(KnowledgeEntry(kind="CONTENT", key=key, value=content, metadata_json=json.dumps({"meaning": meaning, "source": "chat-command"}, ensure_ascii=False), status="MASTER", source=source)); changed = True
            elif record.status != "MASTER":
                record.status = "MASTER"; record.source = source; record.version += 1; changed = True
            if meaning and not db.scalar(select(MelimiExample).where((MelimiExample.melimi_text == content) & (MelimiExample.standard_text == meaning))):
                db.add(MelimiExample(standard_text=meaning, melimi_text=content, category="chat-command", source=source, status="MASTER")); changed = True
            phrases = 1
        if changed:
            version = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
            db.add(KnowledgeVersion(version=(version.version if version else 1) + 1, source=source, checksum=hashlib.sha256(message.encode()).hexdigest()))
        db.commit()
    if changed:
        reload_indexes()
    return {"learned": True, "changed": changed, "roots": roots, "phrases": phrases}


def reload_indexes():
    for module, name in (
        ("app.melimi.root_morphology", "reload_root_dictionary"),
        ("app.melimi.registry", "reload_registry"),
        ("app.melimi.index", "reload_index"),
        ("app.melimi.firewall", "reload_firewall"),
        ("app.retrieval.knowledge", "reload_vocabulary"),
    ):
        try:
            getattr(__import__(module, fromlist=[name]), name)()
        except Exception:
            pass


def install_chat_learning():
    # Explicit commands are processed by the request path. No SQLAlchemy hook
    # is installed because normal conversation must never become language data.
    return None
