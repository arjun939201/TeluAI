"""Authoritative main Melimi dictionary layer.

This module establishes Bangaaru Naanelu as a provenance-aware lexical source
without pretending that the source PDF has already been safely ingested. The
runtime dictionary remains structured data: the morphology engine consumes
MelimiRoot entries, while this layer records richer provenance in
KnowledgeEntry metadata.

Pipeline:
    source extraction -> reviewable entry -> APPROVED -> MASTER runtime

Only APPROVED entries from the declared main dictionary source may be imported.
Unknown, malformed, or unreviewed entries are rejected rather than promoted.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy import select

from app.database import KnowledgeEntry, MelimiRoot, SessionLocal

MAIN_DICTIONARY_ID = "bangaaru_naanelu"
MAIN_DICTIONARY_NAME = "Bangaaru Naanelu"
MAIN_DICTIONARY_AUTHOR = "Vaachaspathy"
MAIN_DICTIONARY_EDITION = "2021"
MAIN_DICTIONARY_VERSION = "1.0"
MAIN_DICTIONARY_SOURCE = f"main_dictionary:{MAIN_DICTIONARY_ID}:{MAIN_DICTIONARY_EDITION}"

ALLOWED_IMPORT_STATUSES = {"APPROVED", "MASTER"}


@dataclass(frozen=True)
class MainDictionaryEntry:
    standard_form: str
    melimi_form: str
    meaning: str = ""
    part_of_speech: str = ""
    grammatical_category: str = ""
    root: str = ""
    derived_forms: tuple[str, ...] = ()
    variants: tuple[str, ...] = ()
    domain: str = ""
    examples: tuple[str, ...] = ()
    notes: str = ""
    source_page: int | None = None
    source_entry: str = ""
    confidence: str = "SOURCE_CONFIRMED"
    status: str = "APPROVED"

    @property
    def source_metadata(self) -> dict[str, Any]:
        return {
            "source_type": "MAIN_DICTIONARY",
            "source_id": MAIN_DICTIONARY_ID,
            "book": MAIN_DICTIONARY_NAME,
            "author": MAIN_DICTIONARY_AUTHOR,
            "edition": MAIN_DICTIONARY_EDITION,
            "dictionary_version": MAIN_DICTIONARY_VERSION,
            "page": self.source_page,
            "source_entry": self.source_entry,
            "confidence": self.confidence,
            "status": "MASTER",
        }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tuple_text(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("List fields must be arrays of strings.")
    return tuple(_text(item) for item in value if _text(item))


def validate_entry(raw: dict[str, Any]) -> MainDictionaryEntry:
    if not isinstance(raw, dict):
        raise ValueError("Dictionary entry must be an object.")

    status = _text(raw.get("status", "APPROVED")).upper()
    if status not in ALLOWED_IMPORT_STATUSES:
        raise ValueError("Only APPROVED or MASTER entries may enter the main dictionary.")

    standard = _text(raw.get("standard_form"))
    melimi = _text(raw.get("melimi_form"))
    if not standard or not melimi:
        raise ValueError("standard_form and melimi_form are required.")
    if len(standard) > 160 or len(melimi) > 160:
        raise ValueError("Dictionary forms must be 160 characters or less.")

    page = raw.get("source_page")
    if page is not None:
        try:
            page = int(page)
        except (TypeError, ValueError) as exc:
            raise ValueError("source_page must be an integer.") from exc
        if page < 1:
            raise ValueError("source_page must be positive.")

    confidence = _text(raw.get("confidence", "SOURCE_CONFIRMED")).upper()
    if confidence not in {"SOURCE_CONFIRMED", "HIGH", "MEDIUM", "LOW", "NEEDS_REVIEW"}:
        raise ValueError("Unsupported confidence value.")
    if confidence == "NEEDS_REVIEW":
        raise ValueError("NEEDS_REVIEW entries cannot be imported into MASTER.")

    return MainDictionaryEntry(
        standard_form=standard,
        melimi_form=melimi,
        meaning=_text(raw.get("meaning")),
        part_of_speech=_text(raw.get("part_of_speech")),
        grammatical_category=_text(raw.get("grammatical_category")),
        root=_text(raw.get("root")) or standard,
        derived_forms=_tuple_text(raw.get("derived_forms")),
        variants=_tuple_text(raw.get("variants")),
        domain=_text(raw.get("domain")),
        examples=_tuple_text(raw.get("examples")),
        notes=_text(raw.get("notes")),
        source_page=page,
        source_entry=_text(raw.get("source_entry")),
        confidence=confidence,
        status=status,
    )


def _knowledge_metadata(entry: MainDictionaryEntry) -> dict[str, Any]:
    return {
        **entry.source_metadata,
        "standard_form": entry.standard_form,
        "melimi_form": entry.melimi_form,
        "meaning": entry.meaning,
        "part_of_speech": entry.part_of_speech,
        "grammatical_category": entry.grammatical_category,
        "root": entry.root,
        "derived_forms": list(entry.derived_forms),
        "variants": list(entry.variants),
        "domain": entry.domain,
        "examples": list(entry.examples),
        "notes": entry.notes,
    }


def import_entries(entries: Iterable[dict[str, Any]], *, replace: bool = True) -> dict[str, int]:
    """Import already-reviewed dictionary entries into the MASTER lexicon.

    Main-dictionary entries have lexical authority over older user/corpus roots.
    The ``replace`` argument is retained for CLI/API compatibility; a main
    dictionary import always promotes a conflicting older root to the protected
    source because otherwise the declared source of truth would not be true.

    This function deliberately accepts structured reviewed entries, not raw PDF
    text. PDF/OCR extraction belongs in a separate review pipeline so corrupted
    extraction can never silently become authoritative language data.
    """
    parsed = [validate_entry(item) for item in entries]
    imported = 0
    skipped = 0

    with SessionLocal() as db:
        for entry in parsed:
            root = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == entry.standard_form))
            if root:
                root.melimi_root = entry.melimi_form
                root.meaning = entry.meaning or root.meaning
                root.category = entry.part_of_speech or root.category
                root.status = "MASTER"
                root.source = MAIN_DICTIONARY_SOURCE
                root.version += 1
            else:
                db.add(MelimiRoot(
                    standard_root=entry.standard_form,
                    melimi_root=entry.melimi_form,
                    meaning=entry.meaning,
                    category=entry.part_of_speech,
                    status="MASTER",
                    source=MAIN_DICTIONARY_SOURCE,
                ))

            key = entry.standard_form.lower()
            existing = db.scalar(select(KnowledgeEntry).where(
                (KnowledgeEntry.kind == "MAIN_DICTIONARY_MAPPING") &
                (KnowledgeEntry.key == key)
            ))
            metadata = json.dumps(_knowledge_metadata(entry), ensure_ascii=False, sort_keys=True)
            if existing:
                existing.value = entry.melimi_form
                existing.metadata_json = metadata
                existing.status = "MASTER"
                existing.source = MAIN_DICTIONARY_SOURCE
                existing.version += 1
            else:
                db.add(KnowledgeEntry(
                    kind="MAIN_DICTIONARY_MAPPING",
                    key=key,
                    value=entry.melimi_form,
                    metadata_json=metadata,
                    status="MASTER",
                    source=MAIN_DICTIONARY_SOURCE,
                ))
            imported += 1
        db.commit()

    return {"validated": len(parsed), "imported": imported, "skipped": skipped}


def lookup(standard_form: str) -> dict[str, Any] | None:
    key = _text(standard_form).lower()
    if not key:
        return None
    with SessionLocal() as db:
        row = db.scalar(select(KnowledgeEntry).where(
            (KnowledgeEntry.kind == "MAIN_DICTIONARY_MAPPING") &
            (KnowledgeEntry.key == key) &
            (KnowledgeEntry.status == "MASTER")
        ))
        if not row:
            return None
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except (TypeError, ValueError):
            metadata = {}
        return {"standard_form": key, "melimi_form": row.value, **metadata}


def is_main_dictionary_root(root: MelimiRoot) -> bool:
    return bool(root and root.source == MAIN_DICTIONARY_SOURCE and root.status == "MASTER")


def manifest() -> dict[str, str]:
    return {
        "source_type": "MAIN_DICTIONARY",
        "source_id": MAIN_DICTIONARY_ID,
        "book": MAIN_DICTIONARY_NAME,
        "author": MAIN_DICTIONARY_AUTHOR,
        "edition": MAIN_DICTIONARY_EDITION,
        "dictionary_version": MAIN_DICTIONARY_VERSION,
        "ingestion_policy": "reviewed structured entries only; raw PDF/OCR never becomes MASTER directly",
    }
