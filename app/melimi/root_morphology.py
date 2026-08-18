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

VERB_SUFFIXES = tuple(sorted([
    "స్తుంది", "స్తున్నారు", "స్తున్నాను", "స్తున్నావు", "స్తున్నాడు", "స్తున్నది",
    "తుంది", "తున్నారు", "తున్నాను", "తున్నావు", "తున్నాడు", "తున్నది",
    "డం", "డానికి", "డంలో", "డాన్ని", "డిగా", "డుతూ", "డిన", "డినది",
    "చడం", "చడానికి", "చడంలో", "చడాన్ని", "చుతూ", "చిన", "చింది",
], key=len, reverse=True))

# Productive passive/participial endings that can occur after a learned
# lexical family.  These are deliberately kept separate from ordinary case
# suffixes so a lexical mapping is never reduced as a random string suffix.
DERIVED_VOICE_SUFFIXES = tuple(sorted([
    "బడిన", "బడింది", "బడే", "బడుతుంది", "బడుతున్న", "బడుతూ",
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


def _verb_candidate(surface, roots):
    """Resolve common finite/non-finite forms to a registered verb family."""
    for suffix in VERB_SUFFIXES:
        if not surface.endswith(suffix) or len(surface) <= len(suffix) + 1:
            continue
        stem = surface[:-len(suffix)]
        candidates = (stem, stem + "ు", stem + "చు")
        for candidate in candidates:
            if candidate in roots:
                return candidate, suffix, "verb"

    # A registered form such as సూచించడం has the lexical family prefix సూచీ
    # before the productive -ంచడం ending. Finite forms such as సూచిస్తుంది
    # preserve that prefix, so resolve them to the same MASTER entry.
    for registered in roots:
        if registered.endswith("ంచడం"):
            family_prefix = registered[:-4]
            if family_prefix and surface.startswith(family_prefix):
                return registered, surface[len(family_prefix):], "verb_family"
        elif registered.endswith("డం"):
            family_prefix = registered[:-2]
            if family_prefix and surface.startswith(family_prefix):
                return registered, surface[len(family_prefix):], "verb_family"
    return None


def _derived_voice_candidate(surface, roots):
    """Resolve passive/participial forms through a mapped nominal family.

    Example: a user may register ``నిర్వచనం = నిర్వల్కు`` and then use
    ``నిర్వచించబడిన``.  ``నిర్వచనం`` is the lexical root while
    ``నిర్వచించు`` is its productive verbal family; the ``బడిన`` operation
    must therefore be reapplied to the mapped root as
    ``నిర్వల్కు + బడిన`` rather than being left untranslated or guessed.

    This is intentionally conservative: only the recognised ``-చనం`` →
    ``-చించు`` family relation is used here. Unknown families remain
    unchanged instead of being invented.
    """
    for suffix in DERIVED_VOICE_SUFFIXES:
        if not surface.endswith(suffix) or len(surface) <= len(suffix) + 2:
            continue
        verbal_stem = surface[:-len(suffix)]
        if not verbal_stem.endswith("చు"):
            continue
        nominal_candidate = verbal_stem[:-2] + "నం"
        if nominal_candidate in roots:
            return nominal_candidate, suffix, "derived_voice"
    return None


def _case_candidate(surface):
    if surface.endswith("ాన్ని") and len(surface) > len("ాన్ని") + 1:
        return surface[:-len("ాన్ని")] + "ం", ACCUSATIVE
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

    verb = _verb_candidate(surface, roots)
    if verb:
        root, operation, kind = verb
        return MorphologicalForm(surface, root, (operation,), (kind,))

    adj = _adjectival_candidate(surface, roots)
    if adj:
        return MorphologicalForm(surface, adj[0], (adj[1],), (adj[2],))

    derived_voice = _derived_voice_candidate(surface, roots)
    if derived_voice:
        root, operation, kind = derived_voice
        return MorphologicalForm(surface, root, (operation,), (kind,))

    def search(current, operations, depth):
        if current in roots:
            return current, operations
        if depth >= 3:
            return None
        candidates = list(_candidate_strips(current, GRAMMATICAL_SUFFIXES, "grammar"))
        candidates += list(_candidate_strips(current, DERIVATIONAL_SUFFIXES, "derivation"))
        for root, suffix, kind in candidates:
            found = search(root, operations + [(kind, suffix)], depth + 1)
            if found:
                return found
        return None

    found = search(surface, [], 0)
    if not found:
        return MorphologicalForm(surface, surface)
    root, ops = found
    return MorphologicalForm(surface, root, tuple(s for _, s in ops), tuple(k for k, _ in ops))


def apply_operation(root, kind, suffix):
    if kind == "verb_family":
        if root.endswith("ంచడం"):
            return root[:-4] + suffix
        if root.endswith("డం"):
            return root[:-2] + suffix
        return root + suffix

    if kind == "verb":
        if suffix == "" or suffix == root:
            return root
        if root.endswith("ు"):
            return root[:-1] + suffix
        return root + suffix

    if kind == "derived_voice":
        return root + suffix

    if kind == "adjective":
        # Productive -మైన is an operation on an -ం source form. The lexical
        # dictionary remains root-only: స్థాపితం → నెలగొల్పిదం, then
        # స్థాపితమైన → నెలగొల్పిదమైన. Never store the derived surface as a
        # separate lexical entry.
        if suffix == "మైన":
            return root[:-1] + "మైన" if root.endswith("ం") else root + "మైన"
        if suffix == "ా":
            return root

    if suffix == "గా" and kind == "adjective_predicate":
        return root + "గా"

    if kind == "case":
        if suffix == ACCUSATIVE:
            return root[:-1] + "ాన్ని" if root.endswith("ం") else root + "ని"
        if suffix == DATIVE:
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
