"""PostgreSQL-backed Melimi Language Space accessors.

The application no longer depends on a repository corpus for runtime language
knowledge. These read-only helpers keep the linguistic engines independent of
the SQLAlchemy model implementation while making the database authoritative.
"""
from __future__ import annotations
import json
from sqlalchemy import select
from app.database import SessionLocal, MelimiRoot, MelimiDocument, MelimiRule, MelimiAffix


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
        return result


def language_rules(limit: int = 100) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiRule).where(MelimiRule.status != "REJECTED").order_by(MelimiRule.id.desc()).limit(limit)).all()
        return [{"name": r.name, "category": r.category, "rule_text": r.rule_text, "operation": r.operation, "status": r.status} for r in rows]


def language_affixes(limit: int = 200) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(MelimiAffix).where(MelimiAffix.status != "REJECTED").order_by(MelimiAffix.id.desc()).limit(limit)).all()
        return [{"form": r.form, "kind": r.kind, "meaning": r.meaning, "applies_to": r.applies_to, "notes": r.notes, "status": r.status} for r in rows]
