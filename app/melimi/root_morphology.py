"""Generic root-first Melimi morphology backed by Language Space.

The dictionary stores a lexical mapping once. Inflected source forms are
reduced to that same root, then the grammatical operation is reapplied to the
learned Melimi root.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")

GRAMMATICAL_SUFFIXES = tuple(sorted([
    "లతో", "లలో", "లకు", "లను", "లని", "లపై", "లకై", "లవల్ల",
    "నుంచి", "నుండి", "యొక్క", "తోటి", "గురించి", "కోసం", "వల్ల",
    "మధ్య", "లోని", "పైన", "తో", "లో", "లు", "ను", "ని", "కు",
    "కి", "గా", "పై", "ల",
], key=len, reverse=True))

DERIVATIONAL_SUFFIXES = tuple(sorted([
    "అలవి", "అల్వి", "అరిది", "అర్ది", "కాను", "కాన్", "మారి",
    "వాను", "వాన్", "పాదు", "పఱ", "కము", "ఇకము", "మాలు", "గము",
    "ఓరు", "ఆది", "ఓలి", "ఓజ", "అంగి", "ఇద", "ద", "అ",
], key=len, reverse=True))

ACCUSATIVE = "ACCUSATIVE"
DATIVE = "DATIVE"


@dataclass(frozen=True)
class MorphologicalForm:
    surface: str
    root: str
    suffixes: Tuple[str, ...] = ()
    kinds: Tuple[str, ...] = ()

    @property
    def operations(self):
        return tuple(zip(self.kinds, self.suffixes))


@lru_cache(maxsize=1)
def load_root_dictionary() -> Dict[str, str]:
    try:
        from app.melimi.db_subject import language_roots
        return language_roots()
    except Exception:
        return {}


def reload_root_dictionary():
    load_root_dictionary.cache_clear()


def _candidate_strips(surface, suffixes, kind):
    for suffix in suffixes:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            yield surface[:-len(suffix)], suffix, kind


def _case_candidate(surface):
    """Reverse common Telugu case allomorphs produced from an -ం noun."""
    # సంతోషం + ని -> సంతోషాన్ని
    if surface.endswith("ాన్ని") and len(surface) > len("ాన్ని") + 1:
        return surface[:-len("ాన్ని")] + "ం", ACCUSATIVE
    # సంతోషం + కి -> సంతోషానికి
    if surface.endswith("ానికి") and len(surface) > len("ానికి") + 1:
        return surface[:-len("ానికి")] + "ం", DATIVE
    return None


def _adjectival_candidate(surface, roots):
    if surface.endswith("మైన") and len(surface) > 4:
        candidate = surface[:-3] + "ం"
        if candidate in roots:
            return candidate, "మైన", "adjective"
    if surface.endswith("గా") and len(surface) > 3:
        candidate = surface[:-2] + "ం"
        if candidate in roots:
            return candidate, "గా", "adjective_predicate"
    if surface.endswith("ా") and len(surface) > 2:
        candidate = surface[:-1]
        if candidate in roots:
            return candidate, "ా", "adjective"
    return None


def reduce_to_root(word, roots=None) -> MorphologicalForm:
    surface = (word or "").strip()
    if not surface:
        return MorphologicalForm("", "")

    roots = roots or load_root_dictionary()
    if surface in roots:
        return MorphologicalForm(surface, surface)

    case = _case_candidate(surface)
    if case and case[0] in roots:
        root, operation = case
        return MorphologicalForm(surface, root, (operation,), ("case",))

    adj = _adjectival_candidate(surface, roots)
    if adj:
        return MorphologicalForm(surface, adj[0], (adj[1],), (adj[2],))

    def search(current, operations, depth):
        if current in roots:
            return current, operations
        if depth >= 3:
            return None
        candidates = list(_candidate_strips(current, GRAMMATICAL_SUFFIXES, "grammar"))
        candidates += list(_candidate_strips(current, DERIVATIONAL_SUFFIXES, "derivation"))
        candidates.sort(key=lambda x: (-len(x[1]), x[0]))
        for root, suffix, kind in candidates:
            found = search(root, operations + [(kind, suffix)], depth + 1)
            if found:
                return found
        return None

    found = search(surface, [], 0)
    if not found:
        return MorphologicalForm(surface, surface)

    root, ops = found
    return MorphologicalForm(
        surface,
        root,
        tuple(s for _, s in ops),
        tuple(k for k, _ in ops),
    )


def apply_operation(root, kind, suffix):
    if suffix in {"ా", "మైన"} and kind == "adjective":
        return root
    if suffix == "గా" and kind == "adjective_predicate":
        return root + "గా"

    if kind == "case":
        if suffix == ACCUSATIVE:
            # Target-side reinflection: non-ం roots take ని; -ం roots take -ాన్ని.
            return root[:-1] + "ాన్ని" if root.endswith("ం") else root + "ని"
        if suffix == DATIVE:
            # Target-side reinflection: non-ం roots take కి; -ం roots take -ానికి.
            return root[:-1] + "ానికి" if root.endswith("ం") else root + "కి"

    if root.endswith("ం") and kind == "grammar":
        stem = root[:-1] + "ా"
        forms = {
            "లు": stem + "లు", "ల": stem + "ల", "లను": stem + "లను",
            "లని": stem + "లని", "లకు": stem + "లకు", "లకై": stem + "లకై",
            "లపై": stem + "లపై", "లతో": stem + "లతో", "లలో": stem + "లలో",
        }
        if suffix in forms:
            return forms[suffix]
        if suffix in {"లో", "తో", "గా", "పై"}:
            return root + suffix
        if suffix in {"కు", "కి"}:
            return stem + "నికి"
        if suffix == "ను":
            return stem + "న్ని"

    return root + suffix


def reapply_operations(melimi_root, form):
    result = melimi_root
    for kind, suffix in reversed(form.operations):
        result = apply_operation(result, kind, suffix)
    return result


def convert_surface(word, roots=None):
    roots = roots or load_root_dictionary()
    form = reduce_to_root(word, roots)
    return reapply_operations(roots[form.root], form) if form.root in roots else word


def convert_text(text, roots=None):
    roots = roots or load_root_dictionary()
    return TELUGU_RE.sub(lambda m: convert_surface(m.group(0), roots), text or "")
