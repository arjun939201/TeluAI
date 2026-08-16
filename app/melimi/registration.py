"""Direct, user-initiated Melimi word registration.

A word submitted through the explicit registration UI or /word command is
intentional language-space input, so it is written directly as MASTER data.
Ordinary chat is handled separately and is never inferred as teaching.
"""
from __future__ import annotations

import hashlib
import json
from sqlalchemy import select
from app.database import SessionLocal, MelimiRoot, KnowledgeEntry, KnowledgeVersion, now, audit_log


def build_entry(data):
    word = str(data.get("word", "")).strip()
    melimi = str(data.get("melimi_equivalent", "")).strip()
    if not word:
        raise ValueError("Source/loan word is required.")
    if not melimi:
        raise ValueError("Melimi Telugu word is required.")
    if len(word) > 160 or len(melimi) > 160:
        raise ValueError("Word entries must be 160 characters or less per side.")
    return {
        "standard_or_source": word,
        "source_root": str(data.get("root") or word).strip(),
        "melimi": melimi,
        "melimi_root": melimi,
        "meaning": str(data.get("meaning", "")).strip(),
        "part_of_speech": str(data.get("part_of_speech", "")).strip(),
        "formation": str(data.get("formation", "")).strip(),
        "status": "MASTER",
        "source": "direct-language-entry",
    }


async def register_word(data, user_id=None):
    entry = build_entry(data)
    source = entry["standard_or_source"]
    target = entry["melimi_root"].split("/")[0].strip()
    with SessionLocal() as db:
        row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == source))
        if row:
            row.melimi_root = target
            row.meaning = entry["meaning"] or row.meaning
            row.category = entry["part_of_speech"] or row.category
            row.status = "MASTER"
            row.source = "direct-language-entry"
            row.version += 1
            row.updated_at = now()
        else:
            row = MelimiRoot(
                standard_root=source,
                melimi_root=target,
                meaning=entry["meaning"],
                category=entry["part_of_speech"],
                status="MASTER",
                source="direct-language-entry",
            )
            db.add(row)
            db.flush()

        key = source.lower()
        knowledge = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == "MELIMI_MAPPING") & (KnowledgeEntry.key == key)))
        metadata = {"source_root": entry["source_root"], "meaning": entry["meaning"], "part_of_speech": entry["part_of_speech"], "formation": entry["formation"]}
        if knowledge:
            knowledge.value = target
            knowledge.metadata_json = json.dumps(metadata, ensure_ascii=False)
            knowledge.status = "MASTER"
            knowledge.source = "direct-language-entry"
            knowledge.version += 1
        else:
            db.add(KnowledgeEntry(kind="MELIMI_MAPPING", key=key, value=target, metadata_json=json.dumps(metadata, ensure_ascii=False), status="MASTER", source="direct-language-entry"))

        current = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        db.add(KnowledgeVersion(version=(current.version if current else 1) + 1, source="direct-language-entry", checksum=hashlib.sha256(f"{source}\n{target}".encode()).hexdigest()))
        db.commit()
        db.refresh(row)

    audit_log(user_id, "language.word.create", "melimi_root", str(row.id), {"source": source, "melimi": target})
    try:
        from app.melimi.root_morphology import reload_root_dictionary
        from app.melimi.registry import reload_registry
        from app.melimi.index import reload_index
        from app.melimi.firewall import reload_firewall
        reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
    except Exception:
        pass
    return {"entry": entry, "id": row.id, "stored": "postgresql_or_local_database", "committed": True, "status": "MASTER"}
