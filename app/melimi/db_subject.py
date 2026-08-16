"""PostgreSQL-backed Melimi Language Space accessors.

PostgreSQL is authoritative for runtime language knowledge. Explicit chat
commands (/word and /content) are represented here too, so newly entered
knowledge becomes retrievable immediately without a separate file corpus.
"""
from __future__ import annotations
import json
from sqlalchemy import select
from app.database import SessionLocal, MelimiRoot, MelimiDocument, MelimiRule, MelimiAffix, KnowledgeEntry


def language_roots() -> dict[str, str]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRoot).where(MelimiRoot.status != "REJECTED")).all()
        return {r.standard_root: r.melimi_root for r in rows if r.standard_root and r.melimi_root}


def language_documents() -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiDocument).where(MelimiDocument.status != "REJECTED")).all()
        result = []
        for row in rows:
            try:
                entries = json.loads(row.entries_json or "[]")
            except (TypeError, ValueError):
                entries = []
            result.append({"path": row.path, "kind": row.kind, "text": row.text, "entries": entries})

        # KnowledgeEntry is the direct-chat/content store. Expose it through
        # the same read-only subject interface so retrieval and the morphology
        # engines see newly entered knowledge without a separate index source.
        knowledge_rows = db.scalars(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.status != "REJECTED")
            .order_by(KnowledgeEntry.id.desc())
            .limit(5000)
        ).all()
        for row in knowledge_rows:
            try:
                metadata = json.loads(row.metadata_json or "{}")
            except (TypeError, ValueError):
                metadata = {}
            kind = "vocabulary" if row.kind.upper() in {"VOCABULARY", "ROOT"} else "prose" if row.kind.upper() in {"CONTENT", "POST", "EXAMPLE"} else row.kind.lower()
            entry = {"key": row.key, "value": row.value, **metadata}
            if row.kind.upper() in {"VOCABULARY", "ROOT"}:
                entry.setdefault("standard", metadata.get("standard", row.key))
                entry.setdefault("melimi", metadata.get("melimi", row.value))
            else:
                entry.setdefault("content", row.value)
            result.append({"path": f"knowledge/{row.id}:{row.key}", "kind": kind, "text": row.value, "entries": [entry]})
        return result


def language_rules(limit: int = 100) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRule).where(MelimiRule.status != "REJECTED").order_by(MelimiRule.id.desc()).limit(limit)).all()
        return [{"name": r.name, "category": r.category, "rule_text": r.rule_text, "operation": r.operation, "status": r.status} for r in rows]


def language_affixes(limit: int = 200) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiAffix).where(MelimiAffix.status != "REJECTED").order_by(MelimiAffix.id.desc()).limit(limit)).all()
        return [{"form": r.form, "kind": r.kind, "meaning": r.meaning, "applies_to": r.applies_to, "notes": r.notes, "status": r.status} for r in rows]
