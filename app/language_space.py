"""Unified Melimi Telugu language-space API and retrieval layer.

The language space is the curated administrative layer for dictionary entries,
posts, grammar, rules, examples, facts, notes and documents. It uses the
existing runtime knowledge tables rather than introducing a second database.
Dictionary entries are bridged to the authoritative MelimiRoot table so edits
made here are immediately usable by the root-first language engine.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, HTTPException, Query
from sqlalchemy import or_, select, func

from app.auth import require_admin
from app.database import SessionLocal, KnowledgeEntry, KnowledgeVersion, MelimiRoot, audit_log, now

ALLOWED_KINDS = {"DICTIONARY", "POST", "GRAMMAR", "RULE", "EXAMPLE", "FACT", "NOTE", "DOCUMENT"}


def _row(row: KnowledgeEntry) -> dict[str, Any]:
    try: metadata = json.loads(row.metadata_json or "{}")
    except Exception: metadata = {}
    return {"id": row.id, "kind": row.kind, "key": row.key, "value": row.value, "metadata": metadata, "status": row.status, "source": row.source, "version": row.version}


def _root_row(row: MelimiRoot) -> dict[str, Any]:
    return {"id": -row.id, "kind": "DICTIONARY", "key": row.standard_root, "value": row.melimi_root,
            "metadata": {"meaning": row.meaning, "category": row.category, "authoritative": True, "source_model": "melimi_roots"},
            "status": row.status, "source": row.source, "version": row.version}


def _bump_version(db, source: str = "admin_language_space") -> int:
    current = db.scalar(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc()))
    version = (current.version if current else 1) + 1
    db.add(KnowledgeVersion(version=version, source=source, checksum="admin-edit"))
    return version


def list_space(kind: str | None = None, q: str | None = None, limit: int = 100):
    limit = max(1, min(limit, 500)); query = (q or "").strip()
    with SessionLocal() as db:
        result = []
        if not kind or kind.upper() == "DICTIONARY":
            stmt = select(MelimiRoot).where(MelimiRoot.status != "REJECTED").order_by(MelimiRoot.updated_at.desc()).limit(limit)
            if query:
                like = f"%{query}%"
                stmt = stmt.where(or_(MelimiRoot.standard_root.ilike(like), MelimiRoot.melimi_root.ilike(like), MelimiRoot.meaning.ilike(like)))
            result.extend(_root_row(r) for r in db.scalars(stmt).all())
        if not kind or kind.upper() != "DICTIONARY":
            stmt = select(KnowledgeEntry).where(KnowledgeEntry.status != "REJECTED")
            if kind and kind.upper() in ALLOWED_KINDS: stmt = stmt.where(KnowledgeEntry.kind == kind.upper())
            if query:
                like = f"%{query}%"; stmt = stmt.where(or_(KnowledgeEntry.key.ilike(like), KnowledgeEntry.value.ilike(like)))
            result.extend(_row(r) for r in db.scalars(stmt.order_by(KnowledgeEntry.id.desc()).limit(limit)).all())
        return result[:limit]


def get_space_entry(entry_id: int):
    with SessionLocal() as db:
        if entry_id < 0:
            row = db.get(MelimiRoot, abs(entry_id)); return _root_row(row) if row and row.status != "REJECTED" else None
        row = db.get(KnowledgeEntry, entry_id); return _row(row) if row and row.status != "REJECTED" else None


def create_space_entry(kind: str, key: str, value: str, metadata: dict[str, Any], actor_id: int):
    kind = kind.upper().strip(); key = key.strip(); value = value.strip(); metadata = metadata or {}
    if kind not in ALLOWED_KINDS: raise ValueError("Unsupported language-space content type.")
    if not key or not value: raise ValueError("Key/title and content are required.")
    if len(key) > 255 or len(value) > 500000: raise ValueError("Language-space content is too large.")
    with SessionLocal() as db:
        if kind == "DICTIONARY":
            row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == key))
            if row:
                row.melimi_root = value.split("/")[0].strip(); row.meaning = str(metadata.get("meaning", row.meaning)); row.category = str(metadata.get("category", row.category)); row.status = "MASTER"; row.source = "admin_language_space"; row.version += 1; row.updated_at = now()
            else:
                row = MelimiRoot(standard_root=key, melimi_root=value.split("/")[0].strip(), meaning=str(metadata.get("meaning", "")), category=str(metadata.get("category", "")), status="MASTER", source="admin_language_space")
                db.add(row); db.flush()
            _bump_version(db); db.commit(); db.refresh(row); result = _root_row(row)
        else:
            row = KnowledgeEntry(kind=kind, key=key, value=value, metadata_json=json.dumps(metadata, ensure_ascii=False), status="MASTER", source="admin_language_space", version=1)
            db.add(row); _bump_version(db); db.commit(); db.refresh(row); result = _row(row)
    audit_log(actor_id, "language_space.create", "language_entry", str(result["id"]), {"kind": kind, "key": key})
    return result


def update_space_entry(entry_id: int, kind: str, key: str, value: str, metadata: dict[str, Any], actor_id: int):
    kind = kind.upper().strip(); key = key.strip(); value = value.strip(); metadata = metadata or {}
    if kind not in ALLOWED_KINDS: raise ValueError("Unsupported language-space content type.")
    if not key or not value: raise ValueError("Key/title and content are required.")
    with SessionLocal() as db:
        if entry_id < 0:
            row = db.get(MelimiRoot, abs(entry_id))
            if not row or row.status == "REJECTED": return None
            if kind != "DICTIONARY": raise ValueError("A dictionary entry must remain a dictionary entry.")
            row.standard_root = key; row.melimi_root = value.split("/")[0].strip(); row.meaning = str(metadata.get("meaning", "")); row.category = str(metadata.get("category", "")); row.status = "MASTER"; row.source = "admin_language_space"; row.version += 1; row.updated_at = now()
            _bump_version(db); db.commit(); db.refresh(row); result = _root_row(row)
        else:
            row = db.get(KnowledgeEntry, entry_id)
            if not row or row.status == "REJECTED": return None
            if row.kind == "DICTIONARY" or kind == "DICTIONARY": raise ValueError("Dictionary entries use the authoritative dictionary records.")
            row.kind = kind; row.key = key; row.value = value; row.metadata_json = json.dumps(metadata, ensure_ascii=False); row.status = "MASTER"; row.source = "admin_language_space"; row.version += 1
            _bump_version(db); db.commit(); db.refresh(row); result = _row(row)
    audit_log(actor_id, "language_space.update", "language_entry", str(entry_id), {"kind": kind, "key": key})
    return result


def delete_space_entry(entry_id: int, actor_id: int):
    with SessionLocal() as db:
        if entry_id < 0:
            row = db.get(MelimiRoot, abs(entry_id))
            if not row or row.status == "REJECTED": return False
            kind, key = "DICTIONARY", row.standard_root; row.status = "REJECTED"; row.version += 1; row.updated_at = now()
        else:
            row = db.get(KnowledgeEntry, entry_id)
            if not row or row.status == "REJECTED": return False
            kind, key = row.kind, row.key; row.status = "REJECTED"; row.version += 1
        _bump_version(db); db.commit()
    audit_log(actor_id, "language_space.delete", "language_entry", str(entry_id), {"kind": kind, "key": key})
    return True


def language_space_context(user_message: str, max_chars: int = 5000) -> str:
    text = (user_message or "").strip()
    if not text: return ""
    terms = []
    for token in text.split():
        token = token.strip(".,!?;:()[]{}\"'`“”‘’").lower()
        if len(token) >= 2 and token not in terms: terms.append(token)
        if len(terms) >= 8: break
    with SessionLocal() as db:
        rows = []
        for term in terms:
            like = f"%{term}%"
            found = db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.status.in_(["MASTER", "APPROVED"])).where(or_(func.lower(KnowledgeEntry.key).like(like), func.lower(KnowledgeEntry.value).like(like))).order_by(KnowledgeEntry.version.desc(), KnowledgeEntry.id.desc()).limit(12)).all()
            rows.extend(found)
            root_found = db.scalars(select(MelimiRoot).where(MelimiRoot.status.in_(["MASTER", "APPROVED"])).where(or_(func.lower(MelimiRoot.standard_root).like(like), func.lower(MelimiRoot.melimi_root).like(like), func.lower(MelimiRoot.meaning).like(like))).order_by(MelimiRoot.version.desc(), MelimiRoot.id.desc()).limit(12)).all()
            rows.extend(root_found)
        unique=[]; seen=set()
        for row in rows:
            ident=(type(row).__name__, row.id)
            if ident not in seen: seen.add(ident); unique.append(row)
            if len(unique)>=24: break
        if not unique:
            unique = db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.status.in_(["MASTER", "APPROVED"])).order_by(KnowledgeEntry.id.desc()).limit(8)).all()
        lines=[]
        for row in unique:
            if isinstance(row, MelimiRoot): lines.append(f"- [DICTIONARY] {row.standard_root}: {row.melimi_root} — {row.meaning}")
            else: lines.append(f"- [{row.kind}] {row.key}: {row.value}")
        return "\n".join(lines)[:max_chars]


def install_routes(app):
    @app.get("/admin/language-space")
    def admin_language_space(kind: str | None = Query(default=None), q: str | None = Query(default=None), limit: int = 100, user=Depends(require_admin)):
        return {"entries": list_space(kind, q, limit), "kinds": sorted(ALLOWED_KINDS), "role": user.role}

    @app.get("/admin/language-space/{entry_id}")
    def admin_language_space_get(entry_id: int, user=Depends(require_admin)):
        result = get_space_entry(entry_id)
        if result is None: raise HTTPException(404, "Language-space entry not found.")
        return result

    @app.post("/admin/language-space")
    def admin_language_space_create(payload: dict, user=Depends(require_admin)):
        try: return {"ok": True, "entry": create_space_entry(payload.get("kind", ""), payload.get("key", ""), payload.get("value", ""), payload.get("metadata", {}), user.id)}
        except ValueError as exc: raise HTTPException(400, str(exc))

    @app.put("/admin/language-space/{entry_id}")
    def admin_language_space_update(entry_id: int, payload: dict, user=Depends(require_admin)):
        try: result = update_space_entry(entry_id, payload.get("kind", ""), payload.get("key", ""), payload.get("value", ""), payload.get("metadata", {}), user.id)
        except ValueError as exc: raise HTTPException(400, str(exc))
        if result is None: raise HTTPException(404, "Language-space entry not found.")
        return {"ok": True, "entry": result}

    @app.delete("/admin/language-space/{entry_id}")
    def admin_language_space_delete(entry_id: int, user=Depends(require_admin)):
        if not delete_space_entry(entry_id, user.id): raise HTTPException(404, "Language-space entry not found.")
        return {"ok": True}
