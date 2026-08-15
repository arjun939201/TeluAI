"""Generic root-first Melimi morphology engine.

Design goal:
    surface form -> reduce to root/operations -> root dictionary lookup ->
    reapply the same grammatical/derivational operations.

The knowledge base stores lexical roots, not every inflected or derived form.
No word-specific derivation table is used here.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Optional, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")

# Longest first. These are grammatical operations, not vocabulary entries.
GRAMMATICAL_SUFFIXES: Tuple[str, ...] = tuple(sorted([
    "లతో", "లలో", "లకు", "లను", "లని", "లపై", "లకై",
    "నుంచి", "నుండి", "యొక్క", "తోటి", "గురించి", "కోసం", "వల్ల", "మధ్య",
    "లోని", "పైన", "తో", "లో", "లు", "ను", "ని", "కు", "కి", "గా", "పై", "ల",
], key=len, reverse=True))

# Documented Melimi derivational operations. These describe mechanisms; they
# do not encode individual words.
DERIVATIONAL_SUFFIXES: Tuple[str, ...] = tuple(sorted([
    "కాను", "కాన్", "మారి", "వాను", "వాన్", "పాదు", "పఱ", "మాలు",
    "కము", "ఇకము", "గము", "ఓరు", "ఆది", "ఓలి", "ఓజ", "అంగి",
    "అలవి", "అల్వి", "అరిది", "అర్ది", "ా", "ి", "తి", "టి", "అటి",
    "ఇటి", "ఇంటి", "ఆటి", "పాటి", "పారు", "బారు",
], key=len, reverse=True))

@dataclass(frozen=True)
class MorphologicalForm:
    surface: str
    root: str
    suffixes: Tuple[str, ...] = ()
    kinds: Tuple[str, ...] = ()

    @property
    def operations(self):
        return tuple(zip(self.kinds, self.suffixes))


def _root_file() -> str:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here, "melimi_telugu", "vocabulary", "root_dictionary.json")


@lru_cache(maxsize=1)
def load_root_dictionary() -> Dict[str, str]:
    with open(_root_file(), encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, str] = {}
    for item in data.get("entries", []):
        source = str(item.get("standard_root", "")).strip()
        target = str(item.get("melimi_root", "")).strip()
        if source and target and item.get("status", "established") != "rejected":
            # A multi-option target is retained as supplied; generation uses
            # the first option as the canonical deterministic form.
            result[source] = target.split("/")[0].strip()
    # Approved chat-learned roots extend the runtime dictionary without
    # modifying the authoritative Git corpus. Database access is optional;
    # the deterministic engine remains fully usable when PostgreSQL is down.
    try:
        from app.database import approved_learning
        for item in approved_learning():
            source = str(item.get("standard_root", "")).strip()
            target = str(item.get("melimi_root", "")).strip()
            if source and target:
                result[source] = target.split("/")[0].strip()
    except Exception:
        pass
    return result


def _candidate_strips(surface: str, suffixes: Iterable[str], kind: str):
    for suffix in suffixes:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            yield surface[:-len(suffix)], suffix, kind


def reduce_to_root(word: str, roots: Optional[Dict[str, str]] = None) -> MorphologicalForm:
    """Reduce a supported surface form to an authoritative lexical root.

    The analyzer may remove up to three documented grammatical/derivational
    operations, but it accepts a path only when the final candidate is an
    authoritative root. This gives broad grammatical coverage without storing
    word-by-word derivative tables.
    """
    surface = (word or "").strip()
    if not surface:
        return MorphologicalForm("", "")
    roots = roots or load_root_dictionary()
    if surface in roots:
        return MorphologicalForm(surface, surface)

    def search(current: str, operations: list[tuple[str, str]], depth: int):
        if current in roots:
            return current, operations
        if depth >= 3:
            return None
        candidates = list(_candidate_strips(current, GRAMMATICAL_SUFFIXES, "grammar"))
        candidates += list(_candidate_strips(current, DERIVATIONAL_SUFFIXES, "derivation"))
        candidates.sort(key=lambda x: (-len(x[1]), x[0]))
        for root, suffix, kind in candidates:
            result = search(root, operations + [(kind, suffix)], depth + 1)
            if result:
                return result
        return None

    found = search(surface, [], 0)
    if not found:
        return MorphologicalForm(surface, surface)
    root, operations = found
    return MorphologicalForm(surface, root, tuple(s for _, s in operations), tuple(k for k, _ in operations))

def apply_operation(root: str, kind: str, suffix: str) -> str:
    """Apply one operation using central morphophonemic rules only.

    These rules operate on grammatical shape, never on individual lexical
    words. A Melimi root ending in ``ం`` belongs to the documented ``-am``
    stem class and changes shape before plural/case material in the same way
    across the vocabulary.
    """
    if suffix in {"ా", "ి"} and kind == "derivation":
        # Telugu orthography represents this derivational/linking vowel as a
        # dependent sign. In the attributive construction it is not emitted
        # as a second vowel on the Melimi root.
        return root

    if root.endswith("ం") and kind == "grammar":
        stem = root[:-1] + "ా"
        am_forms = {
            "లు": stem + "లు",
            "ల": stem + "ల",
            "లను": stem + "లను",
            "లని": stem + "లని",
            "లకు": stem + "లకు",
            "లకై": stem + "లకై",
            "లపై": stem + "లపై",
            "లతో": stem + "లతో",
            "లలో": stem + "లలో",
        }
        if suffix in am_forms:
            return am_forms[suffix]
        # Singular oblique forms of -ం stems retain the nasal before case
        # endings where ordinary Telugu orthography does so.
        if suffix in {"లో", "తో", "గా", "పై"}:
            return root + suffix
        if suffix in {"కు", "కి"}:
            return stem + "నికి"
        if suffix == "ను":
            return stem + "ను"

    return root + suffix


def reapply_operations(melimi_root: str, form: MorphologicalForm) -> str:
    result = melimi_root
    for kind, suffix in form.operations:
        result = apply_operation(result, kind, suffix)
    return result


def convert_surface(word: str, roots: Optional[Dict[str, str]] = None) -> str:
    roots = roots or load_root_dictionary()
    form = reduce_to_root(word, roots)
    if form.root not in roots:
        return word
    return reapply_operations(roots[form.root], form)


def convert_text(text: str, roots: Optional[Dict[str, str]] = None) -> str:
    roots = roots or load_root_dictionary()
    def repl(match: re.Match) -> str:
        token = match.group(0)
        return convert_surface(token, roots)
    return TELUGU_RE.sub(repl, text or "")
