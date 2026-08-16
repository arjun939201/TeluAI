"""Explicit chat commands for TeluAI language knowledge.

Normal conversation never becomes permanent language data. Explicit insertion
commands are parsed here and authoritative writes are performed only by the
request layer for actors allowed to modify MASTER knowledge.
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import select

from app.database import (
    KnowledgeEntry,
    KnowledgeVersion,
    MelimiAffix,
    MelimiExample,
    MelimiRoot,
    MelimiRule,
    SessionLocal,
    now,
)

_COMMAND_RE = re.compile(
    r"^\s*/(?P<kind>word|meaning|content|example|root|affix|rule|phrase|note|correct)\b(?P<body>.*?)\s*$",
    re.I | re.S,
)
_MAPPING_RE = re.compile(r"^\s*(?P<source>.+?)\s*(?:=|→|->)\s*(?P<melimi>.+?)\s*$", re.S)


def parse_command(message: str):
    """Parse explicit language insertion commands."""
    match = _COMMAND_RE.match(message or "")
    if not match:
        return None
    raw_kind = match.group("kind").lower()
    body = match.group("body").strip()

    if raw_kind in {"word", "meaning", "correct"}:
        parsed = _MAPPING_RE.match(body)
        if not parsed:
            raise ValueError(f"Usage: /{raw_kind} source = melimi")
        source = parsed.group("source").strip()
        melimi = parsed.group("melimi").strip()
        if not source or not melimi or len(source) > 160 or len(melimi) > 160:
            raise ValueError("Word entries must be 160 characters or less per side.")
        return "word", {"source": source, "melimi": melimi, "command": raw_kind}

    if not body:
        raise ValueError(f"/{raw_kind} cannot be empty.")
    if len(body) > 50000:
        raise ValueError("Language content is too large. Maximum is 50,000 characters.")

    if raw_kind == "example":
        note = re.match(r"^(.*?)(?:\s*\(([^()]*)\))?\s*$", body, re.S)
        content = (note.group(1) or "").strip()
        meaning = (note.group(2) or "").strip()
    elif raw_kind in {"root", "affix", "rule"}:
        parsed = _MAPPING_RE.match(body)
        if not parsed:
            raise ValueError(f"Usage: /{raw_kind} name = meaning")
        content = parsed.group("source").strip()
        meaning = parsed.group("melimi").strip()
    else:
        content, meaning = body, ""

    if not content:
        raise ValueError(f"/{raw_kind} cannot be empty.")
    return "content", {"content": content, "meaning": meaning, "command": raw_kind}


def _find_root(db, standard: str):
    for candidate in db.scalars(select(MelimiRoot)).all():
        if str(candidate.standard_root or "").strip().casefold() == standard.casefold():
            return candidate
    return None


def _upsert_knowledge(db, kind: str, key: str, value: str, metadata: dict, source: str) -> bool:
    encoded = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    record = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == kind) & (KnowledgeEntry.key == key)))
    if record:
        if record.value == value and record.metadata_json == encoded and record.status == "MASTER":
            return False
        record.value = value
        record.metadata_json = encoded
        record.status = "MASTER"
        record.source = source
        record.version += 1
        return True
    db.add(KnowledgeEntry(kind=kind, key=key, value=value, metadata_json=encoded, status="MASTER", source=source))
    return True


def learn_explicit_teaching(message: str, user_id: int | None = None):
    parsed = parse_command(message)
    if not parsed:
        return {"learned": False, "changed": False, "roots": 0, "phrases": 0}
    kind, payload = parsed
    source = f"chat_command:user:{user_id or 'unknown'}"
    changed = False
    roots = phrases = 0

    with SessionLocal() as db:
        if kind == "word":
            standard = payload["source"].strip()
            melimi = payload["melimi"].strip()
            melimi_root = melimi.split("/")[0].strip()
            row = _find_root(db, standard)
            if row:
                if row.melimi_root != melimi_root or row.status != "MASTER" or row.source != source:
                    row.standard_root = standard
                    row.melimi_root = melimi_root
                    row.status = "MASTER"
                    row.source = source
                    row.version += 1
                    row.updated_at = now()
                    changed = True
            else:
                db.add(MelimiRoot(standard_root=standard, melimi_root=melimi_root, status="MASTER", source=source))
                changed = True

            metadata = {"standard": standard, "melimi": melimi, "command": payload.get("command", "word")}
            changed = _upsert_knowledge(db, "VOCABULARY", f"word:{standard.casefold()}", melimi, metadata, source) or changed
            roots = 1
        else:
            content = payload["content"]
            meaning = payload.get("meaning", "")
            command = payload.get("command", "content")
            key = f"chat:{command}:{hashlib.sha256((content + '\n' + meaning).encode()).hexdigest()}"
            changed = _upsert_knowledge(
                db,
                {"example": "EXAMPLE", "phrase": "PHRASE", "note": "NOTE", "content": "CONTENT", "root": "ROOT", "affix": "AFFIX", "rule": "RULE"}.get(command, "CONTENT"),
                key,
                content,
                {"meaning": meaning, "command": command, "source": "chat-command"},
                source,
            ) or changed

            if command in {"example", "content", "phrase"}:
                if meaning and not db.scalar(select(MelimiExample).where((MelimiExample.melimi_text == content) & (MelimiExample.standard_text == meaning))):
                    db.add(MelimiExample(standard_text=meaning, melimi_text=content, category=command, source=source, status="MASTER"))
                    changed = True
                phrases = 1
            elif command == "root":
                row = _find_root(db, content)
                if row:
                    if row.meaning != meaning or row.status != "MASTER":
                        row.meaning = meaning
                        row.status = "MASTER"
                        row.source = source
                        row.version += 1
                        row.updated_at = now()
                        changed = True
                else:
                    db.add(MelimiRoot(standard_root=content, melimi_root=meaning, meaning=meaning, status="MASTER", source=source))
                    changed = True
                roots = 1
            elif command == "affix":
                existing = db.scalar(select(MelimiAffix).where(MelimiAffix.form == content))
                if existing:
                    if existing.meaning != meaning or existing.status != "MASTER":
                        existing.meaning = meaning
                        existing.status = "MASTER"
                        existing.source = source
                        changed = True
                else:
                    db.add(MelimiAffix(form=content, kind="suffix", meaning=meaning, status="MASTER", source=source))
                    changed = True
            elif command == "rule":
                existing = db.scalar(select(MelimiRule).where(MelimiRule.name == content))
                if existing:
                    if existing.rule_text != meaning or existing.status != "MASTER":
                        existing.rule_text = meaning
                        existing.status = "MASTER"
                        existing.source = source
                        existing.version += 1
                        changed = True
                else:
                    db.add(MelimiRule(name=content, category="chat-command", rule_text=meaning, status="MASTER", source=source))
                    changed = True

        if changed:
            latest = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
            db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source=source, checksum=hashlib.sha256(message.encode()).hexdigest()))
        db.commit()

    if changed:
        reload_indexes()
    return {"learned": True, "changed": changed, "roots": roots, "phrases": phrases}


def reload_indexes():
    """Reload every in-process language index without touching conversations."""
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


def refresh_language_indexes():
    """Public live-refresh hook used by the chat UI/API."""
    reload_indexes()
    return True


def install_chat_learning():
    return None
