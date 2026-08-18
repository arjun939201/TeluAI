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


def language_roots() -> dict[str, str]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRoot).where(MelimiRoot.status == "MASTER")).all()
        return {r.standard_root: r.melimi_root for r in rows if r.standard_root and r.melimi_root}


def language_documents() -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiDocument).where(MelimiDocument.status == "MASTER")).all()
        result = []

        # MASTER roots are authoritative lexical entries too. Expose them through
        # the same retrieval surface used by the language index so /word updates
        # propagate to retrieval without a second manual refresh mechanism.
        root_rows = db.scalars(select(MelimiRoot).where(MelimiRoot.status == "MASTER")).all()
        for row in root_rows:
            if not row.standard_root or not row.melimi_root:
                continue
            entry = {
                "standard": row.standard_root,
                "melimi": row.melimi_root,
                "meaning": row.meaning or row.standard_root,
                "status": row.status,
                "version": row.version,
                "source": row.source,
            }
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
                metadata = json.loads(row.metadata_json or "{}")
            except (TypeError, ValueError):
                metadata = {}
            kind = "vocabulary" if row.kind.upper() in {"VOCABULARY", "ROOT", "MELIMI_MAPPING"} else "prose" if row.kind.upper() in {"CONTENT", "POST", "EXAMPLE"} else row.kind.lower()
            entry = {"key": row.key, "value": row.value, **metadata}
            if row.kind.upper() in {"VOCABULARY", "ROOT", "MELIMI_MAPPING"}:
                entry.setdefault("standard", metadata.get("standard", row.key))
                entry.setdefault("melimi", metadata.get("melimi", row.value))
            else:
                entry.setdefault("content", row.value)
            entry.setdefault("status", row.status)
            entry.setdefault("version", row.version)
            entry.setdefault("source", row.source)
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
