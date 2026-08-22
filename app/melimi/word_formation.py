"""Deterministic, corpus-authorized Melimi word formation.

A derivation is allowed only when both the source root and requested affix are
MASTER records in the shared Melimi Language Space. This module deliberately
does not invent roots, affixes, meanings, or grammatical classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.melimi.db_subject import language_affixes, language_roots, language_space_version


@dataclass(frozen=True)
class FormationResult:
    root: str
    affix: str
    word: str
    status: str
    meaning: str = ""
    kind: str = ""
    applies_to: str = ""
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "root": self.root,
            "affix": self.affix,
            "word": self.word,
            "status": self.status,
            "meaning": self.meaning,
            "kind": self.kind,
            "applies_to": self.applies_to,
            "source": self.source,
        }


@lru_cache(maxsize=16)
def _affix_inventory(version: int) -> tuple[dict, ...]:
    try:
        return tuple(language_affixes())
    except Exception:
        return ()


def reload_word_formation() -> None:
    _affix_inventory.cache_clear()


def _normalize(value: str) -> str:
    return " ".join((value or "").strip().split()).casefold()


def _find_affix(affix: str, version: int) -> dict | None:
    wanted = _normalize(affix)
    for item in _affix_inventory(int(version)):
        forms = [str(item.get("form") or "")]
        # A Language Space record may explicitly document slash-separated
        # variants such as "కాను/కాన్". Treat each documented variant equally.
        for form in list(forms):
            forms.extend(part.strip() for part in form.split("/") if part.strip())
        if any(_normalize(form) == wanted for form in forms):
            return item
    return None


def derive_word(root: str, affix: str, *, version: int | None = None) -> FormationResult:
    """Derive a Melimi word using one authoritative MASTER affix.

    The current implementation uses the corpus spelling operation (suffix
    concatenation). More specialized operations can be added later as explicit
    MASTER rules without changing this API.
    """
    resolved = int(version) if version is not None else int(language_space_version())
    root = (root or "").strip()
    affix = (affix or "").strip()

    if not root or not affix:
        return FormationResult(root, affix, root, "UNSUPPORTED")

    try:
        roots = language_roots()
    except Exception:
        roots = {}

    canonical_root = next((r for r in roots if _normalize(r) == _normalize(root)), None)
    if canonical_root is None:
        return FormationResult(root, affix, root, "UNKNOWN_ROOT")

    record = _find_affix(affix, resolved)
    if record is None or str(record.get("status", "")).upper() != "MASTER":
        return FormationResult(canonical_root, affix, canonical_root, "UNSUPPORTED_AFFIX")

    canonical_affix = next(
        (part.strip() for part in str(record.get("form") or "").split("/")
         if _normalize(part) == _normalize(affix)),
        str(record.get("form") or affix).strip(),
    )

    # Do not silently apply a non-suffix rule. The database's applies_to field
    # remains evidence for callers and future specialized operations.
    word = canonical_root + canonical_affix
    return FormationResult(
        root=canonical_root,
        affix=canonical_affix,
        word=word,
        status="MASTER_DERIVED",
        meaning=str(record.get("meaning") or ""),
        kind=str(record.get("kind") or ""),
        applies_to=str(record.get("applies_to") or ""),
        source=str(record.get("source") or ""),
    )


def derive_many(root: str, *, version: int | None = None, limit: int = 50) -> list[FormationResult]:
    """Generate only formations licensed by MASTER Language Space affixes."""
    resolved = int(version) if version is not None else int(language_space_version())
    results: list[FormationResult] = []
    for item in _affix_inventory(resolved)[: max(1, min(int(limit), 200))]:
        form = str(item.get("form") or "").strip()
        if not form:
            continue
        # For slash variants, return each documented form independently.
        for variant in (part.strip() for part in form.split("/") if part.strip()):
            result = derive_word(root, variant, version=resolved)
            if result.status == "MASTER_DERIVED":
                results.append(result)
    return results
