"""Unified Melimi Telugu language-space API and retrieval layer.

The language space intentionally uses the existing KnowledgeEntry table as a
single authoritative content store for dictionary entries, posts, grammar,
rules, examples, facts and notes. It is not a second database; it is the
curated language layer that the Melimi chat engine reads directly.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, HTTPException, Query
from sqlalchemy import or_, select, func

from app.auth import require_admin
from app.database import SessionLocal, KnowledgeEntry, KnowledgeVersion, now, audit_log

ALLOWED_KINDS = {
    "DICTIONARY", "POST", "GRAMMAR", "RULE", "EXAMPLE", "FACT", "NOTE", "DOCUMENT"
}


def _row(row: KnowledgeEntry) -> dict[str, Any]:
    try:
        metadata = json.loads(row.metadata_json or "{}")
    except Exception:
        metadata = {}
    return {
        "id": row.id,
        "kind": row.kind,
        "key": row.key,
        "value": row.value,
        "metadata": metadata,
        "status": row.status,
        "source": row.source,
        "version": row.version,
    }


def _bump_version(db, source: str = "admin_language_space") -> int:
    current = db.scalar(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc()))
    version = (current.version if current else 1) + 1
    db.add(KnowledgeVersion(version=version, source=source, checksum="admin-edit"))
    return version


def list_space(kind: str | None = None, q: str | None = None, limit: int = 100):
    with SessionLocal() as db:
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.status != "REJECTED")
        if kind and kind.upper() in ALLOWED_KINDS:
            stmt = stmt.where(KnowledgeEntry.kind == kind.upper())
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            stmt = stmt.where(or_(KnowledgeEntry.key.ilike(like), KnowledgeEntry.value.ilike(like)))
        rows = db.scalars(stmt.order_by(KnowledgeEntry.id.desc()).limit(max(1, min(limit, 500)))).all()
        return [_row(r) for r in rows]


def get_space_entry(entry_id: int):
    with SessionLocal() as db:
        row = db.get(KnowledgeEntry, entry_id)
        return _row(row) if row and row.status != "REJECTED" else None


def create_space_entry(kind: str, key: str, value: str, metadata: dict[str, Any], actor_id: int):
    kind = kind.upper().strip()
    key = key.strip()
    value = value.strip()
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unsupported language-space content type.")
    if not key or not value:
        raise ValueError("Key/title and content are required.")
    if len(key) > 255 or len(value) > 500000:
        raise ValueError("Language-space content is too large.")
    with SessionLocal() as db:
        row = KnowledgeEntry(kind=kind, key=key, value=value,
                             metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
                             status="MASTER", source="admin_language_space", version=1)
        db.add(row)
        _bump_version(db)
        db.commit(); db.refresh(row)
        result = _row(row)
    audit_log(actor_id, "language_space.create", "knowledge_entry", str(result["id"]), {"kind": kind, "key": key})
    return result


def update_space_entry(entry_id: int, kind: str, key: str, value: str, metadata: dict[str, Any], actor_id: int):
    kind = kind.upper().strip(); key = key.strip(); value = value.strip()
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unsupported language-space content type.")
    if not key or not value:
        raise ValueError("Key/title and content are required.")
    with SessionLocal() as db:
        row = db.get(KnowledgeEntry, entry_id)
        if not row or row.status == "REJECTED":
            return None
        row.kind = kind; row.key = key; row.value = value
        row.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        row.status = "MASTER"; row.source = "admin_language_space"; row.version += 1
        _bump_version(db)
        db.commit(); db.refresh(row)
        result = _row(row)
    audit_log(actor_id, "language_space.update", "knowledge_entry", str(entry_id), {"kind": kind, "key": key})
    return result


def delete_space_entry(entry_id: int, actor_id: int):
    with SessionLocal() as db:
        row = db.get(KnowledgeEntry, entry_id)
        if not row or row.status == "REJECTED":
            return False
        kind, key = row.kind, row.key
        # Keep an audit-friendly tombstone rather than physically destroying
        # the row. The AI will never retrieve REJECTED entries.
        row.status = "REJECTED"; row.version += 1
        _bump_version(db)
        db.commit()
    audit_log(actor_id, "language_space.delete", "knowledge_entry", str(entry_id), {"kind": kind, "key": key})
    return True


def language_space_context(user_message: str, max_chars: int = 5000) -> str:
    """Retrieve curated language-space evidence relevant to the current chat."""
    text = (user_message or "").strip()
    if not text:
        return ""
    terms = []
    for token in text.split():
        token = token.strip(".,!?;:()[]{}\"'`“”‘’").lower()
        if len(token) >= 2 and token not in terms:
            terms.append(token)
        if len(terms) >= 8:
            break
    with SessionLocal() as db:
        rows = []
        for term in terms:
            like = f"%{term}%"
            found = db.scalars(
                select(KnowledgeEntry)
                .where(KnowledgeEntry.status.in_(["MASTER", "APPROVED"]))
                .where(or_(func.lower(KnowledgeEntry.key).like(like), func.lower(KnowledgeEntry.value).like(like)))
                .order_by(KnowledgeEntry.version.desc(), KnowledgeEntry.id.desc())
                .limit(12)
            ).all()
            rows.extend(found)
        # Preserve order while removing duplicate rows.
        unique = []
        seen = set()
        for row in rows:
            if row.id not in seen:
                seen.add(row.id); unique.append(row)
            if len(unique) >= 24:
                break
        if not unique:
            # A small recent slice gives the model durable language-space
            # experience even when the exact query terms are absent.
            unique = db.scalars(
                select(KnowledgeEntry)
                .where(KnowledgeEntry.status.in_(["MASTER", "APPROVED"]))
                .order_by(KnowledgeEntry.id.desc()).limit(8)
            ).all()
        lines = []
        for row in unique:
            lines.append(f"- [{row.kind}] {row.key}: {row.value}")
        return "\n".join(lines)[:max_chars]


def install_routes(app):
    @app.get("/admin/language-space")
    def admin_language_space(kind: str | None = Query(default=None), q: str | None = Query(default=None), limit: int = 100, user=Depends(require_admin)):
        return {"entries": list_space(kind, q, limit), "kinds": sorted(ALLOWED_KINDS), "role": user.role}

    @app.get("/admin/language-space/{entry_id}")
    def admin_language_space_get(entry_id: int, user=Depends(require_admin)):
        result = get_space_entry(entry_id)
        if result is None:
            raise HTTPException(404, "Language-space entry not found.")
        return result

    @app.post("/admin/language-space")
    def admin_language_space_create(payload: dict, user=Depends(require_admin)):
        try:
            return {"ok": True, "entry": create_space_entry(payload.get("kind", ""), payload.get("key", ""), payload.get("value", ""), payload.get("metadata", {}), user.id)}
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @app.put("/admin/language-space/{entry_id}")
    def admin_language_space_update(entry_id: int, payload: dict, user=Depends(require_admin)):
        try:
            result = update_space_entry(entry_id, payload.get("kind", ""), payload.get("key", ""), payload.get("value", ""), payload.get("metadata", {}), user.id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        if result is None:
            raise HTTPException(404, "Language-space entry not found.")
        return {"ok": True, "entry": result}

    @app.delete("/admin/language-space/{entry_id}")
    def admin_language_space_delete(entry_id: int, user=Depends(require_admin)):
        if not delete_space_entry(entry_id, user.id):
            raise HTTPException(404, "Language-space entry not found.")
        return {"ok": True}
