from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import KnowledgeEntry, KnowledgeVersion, LearningCandidate, MelimiAffix, MelimiDocument, MelimiRoot, MelimiRule, SessionLocal
from app.melimi.content_processor import ContentItem, extract_explicit_items

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
MAP_RE = re.compile(r"^\s*(.+?)\s+(?:→|->|=|[-–—])\s+(.+?)\s*$")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ZIP_MEMBER_BYTES = 5 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 10 * 1024 * 1024
MAX_ZIP_FILES = 50


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


def _structured_entries(obj) -> list[dict]:
    if isinstance(obj, list):
        return [item for item in obj if isinstance(item, dict)]
    if not isinstance(obj, dict):
        return []
    result: list[dict] = []
    for item in obj.get("roots", []):
        if isinstance(item, dict):
            result.append({"standard_root": item.get("standard_root", ""), "melimi_root": item.get("melimi_root", ""), **item})
    for key in ("entries", "vocabulary", "mappings"):
        for item in obj.get(key, []):
            if isinstance(item, dict):
                result.append(item)
    return result


def _upsert_entry(db, entry: dict, source: str) -> bool:
    standard = str(entry.get("standard") or entry.get("standard_root") or entry.get("standard_or_source") or entry.get("source_word") or "").strip()
    melimi = str(entry.get("melimi") or entry.get("melimi_root") or entry.get("word") or entry.get("melimi_equivalent") or "").strip()
    if not standard or not melimi:
        return False
    meaning = str(entry.get("meaning") or entry.get("note") or "").strip()
    category = str(entry.get("category") or entry.get("part_of_speech") or "").strip()
    melimi_root = melimi.split("/")[0].strip()
    row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == standard))
    if row:
        row.melimi_root = melimi_root
        row.meaning = meaning or row.meaning
        row.category = category or row.category
        row.status = "MASTER"
        row.source = source
        row.version += 1
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(MelimiRoot(standard_root=standard, melimi_root=melimi_root, meaning=meaning, category=category, status="MASTER", source=source))
    key = standard.casefold()
    metadata = {k: v for k, v in entry.items() if k not in {"standard", "melimi"}}
    knowledge = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "MELIMI_MAPPING") & (KnowledgeEntry.key == key)))
    if knowledge:
        knowledge.value = melimi_root
        knowledge.metadata_json = json.dumps(metadata, ensure_ascii=False)
        knowledge.status = "MASTER"
        knowledge.source = source
        knowledge.version += 1
    else:
        db.add(KnowledgeEntry(kind="MELIMI_MAPPING", key=key, value=melimi_root, metadata_json=json.dumps(metadata, ensure_ascii=False), status="MASTER", source=source))
    return True


def _store_structured_items(db, text: str, source: str) -> list[dict]:
    """Persist explicit non-vocabulary MT assertions into their native tables."""
    structured: list[dict] = []
    for item in extract_explicit_items(text):
        record = {
            "kind": item.kind,
            "form": item.form,
            "meaning": item.meaning,
            "evidence": item.evidence,
            "metadata": item.metadata,
        }
        structured.append(record)
        if item.kind == "rule":
            name = item.form.strip()
            if not name:
                continue
            row = db.scalar(select(MelimiRule).where(MelimiRule.name == name))
            if row:
                row.rule_text = item.meaning
                row.category = "grammar"
                row.status = "MASTER"
                row.source = source
                row.version += 1
            else:
                db.add(MelimiRule(name=name, category="grammar", rule_text=item.meaning, operation="", status="MASTER", source=source))
        elif item.kind == "language_metadata":
            key = item.form.casefold()
            metadata = dict(item.metadata)
            metadata["evidence"] = item.evidence
            row = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "MELIMI_METADATA") & (KnowledgeEntry.key == key)))
            if row:
                row.value = item.meaning
                row.metadata_json = json.dumps(metadata, ensure_ascii=False)
                row.status = "MASTER"
                row.source = source
                row.version += 1
            else:
                db.add(KnowledgeEntry(kind="MELIMI_METADATA", key=key, value=item.meaning, metadata_json=json.dumps(metadata, ensure_ascii=False), status="MASTER", source=source))
    return structured


def _store_document(db, name: str, text: str, entries: list[dict], source: str) -> None:
    path = f"uploads/{source}/{name}"
    payload = json.dumps(entries, ensure_ascii=False)
    row = db.scalar(select(MelimiDocument).where(MelimiDocument.path == path))
    if row:
        row.text = text
        row.entries_json = payload
        row.kind = "uploaded_content"
        row.source = source
        row.status = "MASTER"
        row.version += 1
    else:
        db.add(MelimiDocument(path=path, kind="uploaded_content", text=text, entries_json=payload, source=source, status="MASTER"))


def _knowledge_version(db) -> int:
    row = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
    return int(row.version) if row else 0


def _invalidate_indexes() -> None:
    try:
        from app.melimi.firewall import reload_firewall
        from app.melimi.index import reload_index
        from app.melimi.registry import reload_registry
        from app.melimi.root_morphology import reload_root_dictionary
        reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
    except Exception:
        pass


def _files(filename: str, raw: bytes) -> list[tuple[str, bytes]]:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Language content file is too large. Maximum is 10 MB.")
    extension = os.path.splitext(filename.lower())[1]
    if extension != ".zip":
        return [(os.path.basename(filename) or "language_content" + extension, raw)]

    result: list[tuple[str, bytes]] = []
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if len(members) > MAX_ZIP_FILES:
                raise ValueError(f"ZIP contains too many files. Maximum is {MAX_ZIP_FILES}.")
            for info in members:
                name = os.path.basename(info.filename)
                extension2 = os.path.splitext(name.lower())[1]
                if not name or name.startswith(".") or extension2 not in {".txt", ".md", ".json"}:
                    continue
                if info.file_size > MAX_ZIP_MEMBER_BYTES:
                    raise ValueError(f"File too large inside ZIP: {name}")
                total += info.file_size
                if total > MAX_ZIP_TOTAL_BYTES:
                    raise ValueError("Uncompressed ZIP content exceeds the 10 MB total limit.")
                result.append((name, archive.read(info)))
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid ZIP file.") from exc
    if not result:
        raise ValueError("ZIP contains no supported .txt, .md, or .json language-content files.")
    return result


def _entries_for_text(text: str) -> list[dict]:
    entries: list[dict] = []
    for line in text.splitlines():
        entries.extend(parse_mapping_line(line))
    return entries


def ingest_language_package(filename: str, raw: bytes, approved: bool, actor_user_id: int | None = None):
    files = _files(filename, raw)
    if not approved:
        payload = {
            "filename": filename,
            "bytes": len(raw),
            "files": [{"name": name, "content": data.decode("utf-8-sig", "replace")} for name, data in files],
        }
        with SessionLocal() as db:
            candidate = LearningCandidate(user_id=actor_user_id, knowledge_type="LANGUAGE_PACKAGE", source_text=filename, payload_json=json.dumps(payload, ensure_ascii=False), status="PENDING")
            db.add(candidate); db.commit(); db.refresh(candidate)
            return {"status": "PENDING", "candidate_id": candidate.id, "files": len(files)}

    source = f"upload:{filename}:user:{actor_user_id or 0}"
    counts = {"files": 0, "documents": 0, "mappings": 0, "rules": 0, "metadata": 0}
    with SessionLocal() as db:
        for name, data in files:
            text = data.decode("utf-8-sig", "replace")
            extension = os.path.splitext(name.lower())[1]
            if extension == ".json":
                try:
                    entries = _structured_entries(json.loads(text))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {name}: {exc}") from exc
                structured = []
            else:
                entries = _entries_for_text(text)
                structured = _store_structured_items(db, text, source)
            for entry in entries:
                if _upsert_entry(db, entry, source):
                    counts["mappings"] += 1
            counts["rules"] += sum(1 for item in structured if item["kind"] == "rule")
            counts["metadata"] += sum(1 for item in structured if item["kind"] == "language_metadata")
            combined = entries + structured
            _store_document(db, name, text, combined, source)
            counts["files"] += 1
            counts["documents"] += 1
        db.add(KnowledgeVersion(version=_knowledge_version(db) + 1, source=source, checksum=hashlib.sha256(raw).hexdigest()))
        db.commit()
    _invalidate_indexes()
    return {"status": "APPROVED", "files": counts["files"], "documents": counts["documents"], "counts": counts}


def submit_content(user_id: int, title: str, content: str, meaning: str = "", approved: bool = False):
    title = title.strip()
    content = content.strip()
    meaning = meaning.strip()
    if not content:
        raise ValueError("Content is required.")
    if len(content) > 50000:
        raise ValueError("Content is too large.")
    if approved:
        return ingest_language_package((title or "pasted-content") + ".txt", content.encode("utf-8"), True, user_id)
    payload = {"title": title, "content": content, "meaning": meaning, "kind": "CONTENT"}
    with SessionLocal() as db:
        candidate = LearningCandidate(user_id=user_id, knowledge_type="CONTENT", source_text=f"CONTENT:{title}" if title else "CONTENT", payload_json=json.dumps(payload, ensure_ascii=False), status="PENDING")
        db.add(candidate); db.commit(); db.refresh(candidate)
        return {"status": "PENDING", "candidate_id": candidate.id}


def approve_candidate(candidate_id: int, reviewer_note: str = ""):
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if not candidate:
            return None
        payload = json.loads(candidate.payload_json or "{}")
        kind = candidate.knowledge_type
        candidate.status = "APPROVED"
        candidate.reviewed_at = datetime.now(timezone.utc)
        payload["reviewer_note"] = reviewer_note
        candidate.payload_json = json.dumps(payload, ensure_ascii=False)
        db.commit()

    if kind == "CONTENT":
        result = submit_content(candidate.user_id or 0, payload.get("title", ""), payload.get("content", ""), payload.get("meaning", ""), approved=True)
    elif kind == "LANGUAGE_PACKAGE":
        files = payload.get("files", [])
        source = f"approved-package:{payload.get('filename', candidate.source_text)}:reviewed"
        counts = {"files": 0, "documents": 0, "mappings": 0, "rules": 0, "metadata": 0}
        with SessionLocal() as db:
            for item in files:
                name = str(item.get("name", "")).strip()
                text = str(item.get("content", ""))
                extension = os.path.splitext(name.lower())[1]
                if extension == ".json":
                    try:
                        entries = _structured_entries(json.loads(text))
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid JSON in {name}: {exc}") from exc
                    structured = []
                else:
                    entries = _entries_for_text(text)
                    structured = _store_structured_items(db, text, source)
                for entry in entries:
                    if _upsert_entry(db, entry, source):
                        counts["mappings"] += 1
                counts["rules"] += sum(1 for x in structured if x["kind"] == "rule")
                counts["metadata"] += sum(1 for x in structured if x["kind"] == "language_metadata")
                _store_document(db, name, text, entries + structured, source)
                counts["files"] += 1
                counts["documents"] += 1
            db.add(KnowledgeVersion(version=_knowledge_version(db) + 1, source=source, checksum=hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()))
            db.commit()
        result = {"status": "APPROVED", "files": counts["files"], "documents": counts["documents"], "counts": counts}
    else:
        return {"id": candidate_id, "status": "APPROVED", "payload": payload}
    _invalidate_indexes()
    return {"id": candidate_id, "status": "APPROVED", "payload": payload, **result}


def review_candidate(candidate_id: int, approve: bool, reviewer_note: str = ""):
    if approve:
        return approve_candidate(candidate_id, reviewer_note)
    with SessionLocal() as db:
        candidate = db.get(LearningCandidate, candidate_id)
        if not candidate:
            return None
        payload = json.loads(candidate.payload_json or "{}")
        payload["reviewer_note"] = reviewer_note
        candidate.status = "REJECTED"
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.payload_json = json.dumps(payload, ensure_ascii=False)
        db.commit()
        return {"id": candidate_id, "status": "REJECTED", "payload": payload}
