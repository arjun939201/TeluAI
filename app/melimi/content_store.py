from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import (
    SessionLocal,
    MelimiRoot,
    MelimiDocument,
    KnowledgeEntry,
    KnowledgeVersion,
    LearningCandidate,
)

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
MAP_RE = re.compile(r"^\s*(.+?)\s+(?:→|->|=|[-–—])\s+(.+?)\s*$")


def _has_telugu(value: str) -> bool:
    return bool(TELUGU_RE.search(value or ""))


def _clean_aliases(value: str) -> list[str]:
    value = re.sub(r"\s+", " ", value.strip())
    parts = re.split(r"[,;|/]\s*|\s*\.\s*", value)
    result: list[str] = []
    for part in parts:
        part = part.strip(" .,:;|")
        if part and len(part) <= 255 and part not in result:
            result.append(part)
    return result or [value]


def parse_mapping_line(line: str) -> list[dict]:
    text = line.strip()
    if not text or text.startswith("#"):
        return []
    match = MAP_RE.match(text)
    if not match:
        return []
    left, right = match.group(1).strip(), match.group(2).strip()
    if len(left) > 255 or len(right) > 1000:
        return []
    left_telugu = _has_telugu(left)
    right_telugu = _has_telugu(right)
    if left_telugu and not right_telugu:
        melimi, aliases = left, _clean_aliases(right)
    elif right_telugu and not left_telugu:
        melimi, aliases = right, [left]
    else:
        melimi, aliases = left, [right]
    return [{"standard": alias, "melimi": melimi, "source_type": "uploaded_mapping", "status": "master"} for alias in aliases if alias]


def parse_text(text: str) -> list[dict]:
    entries: list[dict] = []
    for line in text.splitlines():
        entries.extend(parse_mapping_line(line))
    return entries


def _structured_entries(obj) -> list[dict]:
    if isinstance(obj, list): return [item for item in obj if isinstance(item, dict)]
    if not isinstance(obj, dict): return []
    result: list[dict] = []
    for item in obj.get("roots", []):
        if isinstance(item, dict): result.append({"standard_root": item.get("standard_root", ""), "melimi_root": item.get("melimi_root", ""), **item})
    for key in ("entries", "vocabulary", "mappings"):
        for item in obj.get(key, []):
            if isinstance(item, dict): result.append(item)
    return result


def _upsert_entry(db, entry: dict, source: str) -> bool:
    standard = str(entry.get("standard") or entry.get("standard_root") or entry.get("standard_or_source") or entry.get("source_word") or "").strip()
    melimi = str(entry.get("melimi") or entry.get("melimi_root") or entry.get("word") or entry.get("melimi_equivalent") or "").strip()
    if not standard or not melimi: return False
    meaning = str(entry.get("meaning") or entry.get("note") or "").strip()
    category = str(entry.get("category") or entry.get("part_of_speech") or "").strip()
    melimi_root = melimi.split("/")[0].strip()
    row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == standard))
    if row:
        row.melimi_root = melimi_root; row.meaning = meaning or row.meaning; row.category = category or row.category; row.status = "MASTER"; row.source = source; row.version += 1; row.updated_at = datetime.now(timezone.utc)
    else: db.add(MelimiRoot(standard_root=standard, melimi_root=melimi_root, meaning=meaning, category=category, status="MASTER", source=source))
    key = standard.lower(); metadata = {k: v for k, v in entry.items() if k not in {"standard", "melimi"}}
    knowledge = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "MELIMI_MAPPING") & (KnowledgeEntry.key == key)))
    if knowledge:
        knowledge.value = melimi_root; knowledge.metadata_json = json.dumps(metadata, ensure_ascii=False); knowledge.status = "MASTER"; knowledge.source = source; knowledge.version += 1
    else: db.add(KnowledgeEntry(kind="MELIMI_MAPPING", key=key, value=melimi_root, metadata_json=json.dumps(metadata, ensure_ascii=False), status="MASTER", source=source))
    return True


def _store_document(db, name: str, text: str, entries: list[dict], source: str) -> None:
    path = f"uploads/{source}/{name}"; payload = json.dumps(entries, ensure_ascii=False)
    row = db.scalar(select(MelimiDocument).where(MelimiDocument.path == path))
    if row:
        row.text = text; row.entries_json = payload; row.kind = "uploaded_content"; row.source = source; row.status = "MASTER"; row.version += 1
    else: db.add(MelimiDocument(path=path, kind="uploaded_content", text=text, entries_json=payload, source=source, status="MASTER"))


def _knowledge_version(db) -> int:
    row = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
    return int(row.version) if row else 0


def _invalidate_indexes() -> None:
    try:
        from app.melimi.root_morphology import reload_root_dictionary
        from app.melimi.registry import reload_registry
        from app.melimi.index import reload_index
        from app.melimi.firewall import reload_firewall
        reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
    except Exception:
        pass


def _files(filename: str, raw: bytes) -> list[tuple[str, bytes]]:
    extension = os.path.splitext(filename.lower())[1]
    if extension != ".zip": return [(os.path.basename(filename) or "language_content" + extension, raw)]
    result: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for info in archive.infolist():
                if info.is_dir(): continue
                name = os.path.basename(info.filename)
                if not name or name.startswith("."): continue
                if os.path.splitext(name.lower())[1] not in {".txt", ".md", ".json"}: continue
                if info.file_size > 5 * 1024 * 1024: raise ValueError(f"File too large inside ZIP: {name}")
                result.append((name, archive.read(info)))
    except zipfile.BadZipFile as exc: raise ValueError("Invalid ZIP file.") from exc
    if not result: raise ValueError("ZIP contains no supported .txt, .md, or .json language-content files.")
    return result


def ingest_language_package(filename: str, raw: bytes, approved: bool, actor_user_id: int | None = None):
    if len(raw) > 10 * 1024 * 1024: raise ValueError("Language content file is too large. Maximum is 10 MB.")
    files = _files(filename, raw)
    if not approved:
        payload = {"filename": filename, "bytes": len(raw), "files": [{"name": name, "content": data.decode("utf-8-sig", "replace")} for name, data in files]}
        with SessionLocal() as db:
            candidate = LearningCandidate(user_id=actor_user_id, knowledge_type="LANGUAGE_PACKAGE", source_text=filename, payload_json=json.dumps(payload, ensure_ascii=False), status="PENDING")
            db.add(candidate); db.commit(); db.refresh(candidate); return {"status": "PENDING", "candidate_id": candidate.id, "files": len(files)}
    source = f"upload:{filename}"; counts = {"files": 0, "documents": 0, "mappings": 0}
    with SessionLocal() as db:
        for name, data in files:
            text = data.decode("utf-8-sig", "replace"); extension = os.path.splitext(name.lower())[1]
            if extension == ".json":
                try: entries = _structured_entries(json.loads(text))
                except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON in {name}: {exc}") from exc
            else: entries = parse_text(text)
            for entry in entries:
                if _upsert_entry(db, entry, source): counts["mappings"] += 1
            _store_document(db, name, text, entries, source); counts["files"] += 1; counts["documents"] += 1
        db.add(KnowledgeVersion(version=_knowledge_version(db) + 1, source=source, checksum=hashlib.sha256(raw).hexdigest())); db.commit()
    _invalidate_indexes(); return {"status": "APPROVED", "files": counts["files"], "documents": counts["documents"], "counts": counts}


def submit_content(user_id: int, title: str, content: str, approved: bool = False):
    content = content.strip()
    if not content: raise ValueError("Content is required.")
    if len(content) > 50000: raise ValueError("Content is too large.")
    if approved: return ingest_language_package((title.strip() or "pasted-content") + ".txt", content.encode("utf-8"), True, user_id)
    payload = {"title": title.strip(), "content": content, "kind": "CONTENT"}
    with SessionLocal() as db:
        candidate = LearningCandidate(user_id=user_id, knowledge_type="CONTENT", source_text=f"CONTENT:{title.strip()}" if title.strip() else "CONTENT", payload_json=json.dumps(payload, ensure_ascii=False), status="PENDING")
        db.add(candidate); db.commit(); db.refresh(candidate); return {"status": "PENDING", "candidate_id": candidate.id}


def approve_candidate(candidate_id: int, reviewer_note: str = ""):
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if not candidate: return None
        if candidate.knowledge_type == "CONTENT":
            payload = json.loads(candidate.payload_json or "{}"); candidate.status = "APPROVED"; candidate.reviewed_at = datetime.now(timezone.utc); db.commit()
        elif candidate.knowledge_type == "LANGUAGE_PACKAGE":
            payload = json.loads(candidate.payload_json or "{}"); candidate.status = "APPROVED"; candidate.reviewed_at = datetime.now(timezone.utc); db.commit()
        else: return {"id": candidate_id, "status": "APPROVED"}
    if candidate.knowledge_type == "CONTENT":
        result = submit_content(candidate.user_id or 0, payload.get("title", ""), payload.get("content", ""), approved=True)
    else:
        files = payload.get("files", []); source = f"approved-package:{payload.get('filename', candidate.source_text)}"; counts = {"files": 0, "documents": 0, "mappings": 0}
        with SessionLocal() as db:
            for item in files:
                name = str(item.get("name", "")).strip(); text = str(item.get("content", "")); extension = os.path.splitext(name.lower())[1]
                if extension == ".json":
                    try: entries = _structured_entries(json.loads(text))
                    except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON in {name}: {exc}") from exc
                else: entries = parse_text(text)
                for entry in entries:
                    if _upsert_entry(db, entry, source): counts["mappings"] += 1
                _store_document(db, name, text, entries, source); counts["files"] += 1; counts["documents"] += 1
            db.add(KnowledgeVersion(version=_knowledge_version(db) + 1, source=source, checksum=hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest())); db.commit()
        result = {"status": "APPROVED", "files": counts["files"], "documents": counts["documents"], "counts": counts}
    _invalidate_indexes(); return {"id": candidate_id, "status": "APPROVED", "payload": payload, **result}


def review_candidate(candidate_id: int, approve: bool, reviewer_note: str = ""):
    if approve: return approve_candidate(candidate_id, reviewer_note)
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if not candidate: return None
        candidate.status = "REJECTED"; candidate.reviewed_at = datetime.now(timezone.utc); db.commit()
        return {"id": candidate_id, "status": "REJECTED"}
