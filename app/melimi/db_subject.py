"""PostgreSQL-backed Melimi Language Space accessors.

PostgreSQL is authoritative for runtime language knowledge. Explicit chat
commands (/word and /content) are represented here too, so newly entered
knowledge becomes retrievable immediately without a separate file corpus.
"""
from __future__ import annotations
import json
from sqlalchemy import select
from app.database import SessionLocal, MelimiRoot, MelimiDocument, MelimiRule, MelimiAffix, KnowledgeEntry, KnowledgeVersion


def language_space_version() -> int:
    """Return the shared runtime version used to invalidate process-local caches."""
    with SessionLocal() as db:
        return int(db.scalar(select(KnowledgeVersion.version).order_by(KnowledgeVersion.version.desc()).limit(1)) or 0)


def _metadata_by_standard(db) -> dict[str, dict]:
    """Return structured lexical metadata already stored in Language Space."""
    rows = db.scalars(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.status == "MASTER")
        .where(KnowledgeEntry.kind.in_(("VOCABULARY", "ROOT", "MELIMI_MAPPING")))
    ).all()
    result: dict[str, dict] = {}
    for row in rows:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except (TypeError, ValueError):
            metadata = {}
        standard = str(metadata.get("standard") or row.key or "").strip()
        if standard:
            result[standard.casefold()] = metadata
    return result


def language_roots() -> dict[str, str]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRoot).where(MelimiRoot.status == "MASTER")).all()
        return {r.standard_root: r.melimi_root for r in rows if r.standard_root and r.melimi_root}


def language_lexical_entries(limit: int = 5000) -> list[dict]:
    """Return authoritative lemma-level lexical entries with structured metadata."""
    limit = max(1, min(int(limit), 10000))
    with SessionLocal() as db:
        rows = db.scalars(
            select(MelimiRoot)
            .where(MelimiRoot.status == "MASTER")
            .order_by(MelimiRoot.id.desc())
            .limit(limit)
        ).all()
        metadata = _metadata_by_standard(db)
        result = []
        for row in rows:
            if not row.standard_root or not row.melimi_root:
                continue
            item = dict(metadata.get(row.standard_root.casefold(), {}))
            item.update({
                "standard": row.standard_root,
                "melimi": row.melimi_root,
                "meaning": row.meaning or row.standard_root,
                "category": row.category,
                "status": row.status,
                "version": row.version,
                "source": row.source,
            })
            item.setdefault("authority", row.status)
            item.setdefault("standard_lemma", row.standard_root)
            item.setdefault("melimi_lemma", row.melimi_root)
            result.append(item)
        return result


def language_documents() -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiDocument).where(MelimiDocument.status == "MASTER")).all()
        result = []
        metadata = _metadata_by_standard(db)

        # MASTER roots are authoritative lexical entries too. Expose them through
        # the same retrieval surface used by the language index so /word updates
        # propagate to retrieval without a second manual refresh mechanism.
        root_rows = db.scalars(select(MelimiRoot).where(MelimiRoot.status == "MASTER")).all()
        for row in root_rows:
            if not row.standard_root or not row.melimi_root:
                continue
            entry = dict(metadata.get(row.standard_root.casefold(), {}))
            entry.update({
                "standard": row.standard_root,
                "melimi": row.melimi_root,
                "meaning": row.meaning or row.standard_root,
                "category": row.category,
                "status": row.status,
                "version": row.version,
                "source": row.source,
                "authority": row.status,
                "standard_lemma": row.standard_root,
                "melimi_lemma": row.melimi_root,
            })
            result.append({
                "path": f"roots/{row.id}:{row.standard_root}",
                "kind": "vocabulary",
                "text": f"{row.standard_root} {row.melimi_root} {row.meaning or ''}",
                "entries": [entry],
                "status": row.status,
                "version": row.version,
                "source": row.source,
            })

        for row in rows:
            try:
                entries = json.loads(row.entries_json or "[]")
            except (TypeError, ValueError):
                entries = []
            result.append({"path": row.path, "kind": row.kind, "text": row.text, "entries": entries, "status": row.status, "version": row.version, "source": row.source})

        knowledge_rows = db.scalars(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.status == "MASTER")
            .order_by(KnowledgeEntry.id.desc())
            .limit(5000)
        ).all()
        for row in knowledge_rows:
            try:
                metadata_row = json.loads(row.metadata_json or "{}")
            except (TypeError, ValueError):
                metadata_row = {}
            kind = "vocabulary" if row.kind.upper() in {"VOCABULARY", "ROOT", "MELIMI_MAPPING"} else "prose" if row.kind.upper() in {"CONTENT", "POST", "EXAMPLE"} else row.kind.lower()
            entry = {"key": row.key, "value": row.value, **metadata_row}
            if row.kind.upper() in {"VOCABULARY", "ROOT", "MELIMI_MAPPING"}:
                entry.setdefault("standard", metadata_row.get("standard", row.key))
                entry.setdefault("melimi", metadata_row.get("melimi", row.value))
                entry.setdefault("standard_lemma", entry.get("standard"))
                entry.setdefault("melimi_lemma", entry.get("melimi"))
            else:
                entry.setdefault("content", row.value)
            entry.setdefault("status", row.status)
            entry.setdefault("version", row.version)
            entry.setdefault("source", row.source)
            entry.setdefault("authority", row.status)
            result.append({"path": f"knowledge/{row.id}:{row.key}", "kind": kind, "text": row.value, "entries": [entry], "status": row.status, "version": row.version, "source": row.source})
        return result


def language_rules(limit: int = 100) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRule).where(MelimiRule.status == "MASTER").order_by(MelimiRule.id.desc()).limit(limit)).all()
        return [{"name": r.name, "category": r.category, "rule_text": r.rule_text, "operation": r.operation, "status": r.status, "version": r.version, "source": r.source} for r in rows]


def language_affixes(limit: int = 200) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiAffix).where(MelimiAffix.status == "MASTER").order_by(MelimiAffix.id.desc()).limit(limit)).all()
        return [{"form": r.form, "kind": r.kind, "meaning": r.meaning, "applies_to": r.applies_to, "notes": r.notes, "status": r.status, "source": r.source} for r in rows]
