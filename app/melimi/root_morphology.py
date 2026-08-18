"""Root-first Melimi morphology with corpus-backed derivation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")
GRAMMATICAL_SUFFIXES = tuple(sorted([
    "లతో", "లలో", "లకు", "లను", "లని", "లపై", "లకై", "లవల్ల",
    "నుంచి", "నుండి", "యొక్క", "తోటి", "గురించి", "కోసం", "వల్ల", "మధ్య",
    "లోని", "పైన", "తో", "లో", "లు", "న్ని", "ాన్ని", "ానికి", "ను", "ని",
    "కు", "కి", "గా", "పై", "ల",
], key=len, reverse=True))
VERB_SUFFIXES = tuple(sorted([
    "స్తుంది", "స్తున్నారు", "స్తున్నాను", "స్తున్నావు", "స్తున్నాడు", "స్తున్నది",
    "తుంది", "తున్నారు", "తున్నాను", "తున్నావు", "తున్నాడు", "తున్నది", "డం",
    "డానికి", "డంలో", "డాన్ని", "డిగా", "డుతూ", "డిన", "డినది", "చడం",
    "చడానికి", "చడంలో", "చడాన్ని", "చుతూ", "చిన", "చింది",
], key=len, reverse=True))
DERIVED_VOICE_SUFFIXES = tuple(sorted([
    "బడిన", "బడింది", "బడే", "బడుతుంది", "బడుతున్న", "బడుతూ",
], key=len, reverse=True))
DERIVATIONAL_SUFFIXES = tuple(sorted([
    "అలవి", "అల్వి", "అరిది", "అర్ది", "కాను", "కాన్", "మారి", "వాను", "వాన్",
    "పాదు", "పఱ", "కము", "ఇకము", "మాలు", "గము", "ఓరు", "ఆది", "ఓలి", "ఓజ",
    "అంగి", "ఇద", "ద", "అ", "పు",
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


def _plural_candidate(surface, roots):
    if surface.endswith("ాలు") and len(surface) > 4:
        candidate = surface[:-3] + "ం"
        if candidate in roots:
            return candidate, "ాలు", "plural"
    if surface.endswith("ాల") and len(surface) > 3:
        candidate = surface[:-2] + "ం"
        if candidate in roots:
            return candidate, "ాలు", "plural"
    if surface.endswith("లు") and len(surface) > 3:
        candidate = surface[:-2]
        if candidate in roots:
            return candidate, "లు", "plural"
    if surface.endswith("ల") and len(surface) > 2:
        candidate = surface[:-1]
        if candidate in roots:
            return candidate, "లు", "plural"
    for root in roots:
        if roots.get(root) == surface:
            return root, "LEXICAL_PLURAL", "lexical_plural"
    return None


def _verb_candidate(surface, roots):
    for suffix in VERB_SUFFIXES:
        if not surface.endswith(suffix) or len(surface) <= len(suffix) + 1:
            continue
        stem = surface[:-len(suffix)]
        for candidate in (stem, stem + "ు", stem + "చు"):
            if candidate in roots:
                return candidate, suffix, "verb"
    for registered in roots:
        if registered.endswith("ంచడం"):
            prefix = registered[:-4]
            if prefix and surface.startswith(prefix):
                return registered, surface[len(prefix):], "verb_family"
        elif registered.endswith("డం"):
            prefix = registered[:-2]
            if prefix and surface.startswith(prefix):
                return registered, surface[len(prefix):], "verb_family"
    return None


def _derived_voice_candidate(surface, roots):
    for suffix in DERIVED_VOICE_SUFFIXES:
        if not surface.endswith(suffix) or len(surface) <= len(suffix) + 2:
            continue
        stem = surface[:-len(suffix)]
        if stem.endswith("ించ"):
            candidate = stem[:-3] + "నం"
            if candidate in roots:
                return candidate, suffix, "derived_voice"
    return None


def _case_candidate(surface, roots):
    if surface.endswith("ాన్ని"):
        candidate = surface[:-5] + "ం"
        if candidate in roots:
            return candidate, "ను", ACCUSATIVE
    if surface.endswith("ానికి"):
        candidate = surface[:-6] + "ం"
        if candidate in roots:
            return candidate, "కు", DATIVE
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
            return candidate, "ా", "adjective_invariant"
    if surface.endswith("పు") and len(surface) > 3:
        candidate = surface[:-2]
        if candidate + "ం" in roots:
            return candidate + "ం", "పు", "relational_adjective"
    if surface + "ం" in roots:
        return surface + "ం", "BARE_AM", "bare_nominal"
    return None


def reduce_to_root(word, roots=None) -> MorphologicalForm:
    surface = (word or "").strip()
    if not surface:
        return MorphologicalForm("", "")
    roots = roots or load_root_dictionary()
    if surface in roots:
        return MorphologicalForm(surface, surface)
    case = _case_candidate(surface, roots)
    if case:
        root, operation, kind = case
        return MorphologicalForm(surface, root, (operation,), (kind,))
    plural = _plural_candidate(surface, roots)
    if plural:
        root, operation, kind = plural
        return MorphologicalForm(surface, root, (operation,), (kind,))
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
        if depth >= 4:
            return None
        plural = _plural_candidate(current, roots)
        if plural:
            root, suffix, kind = plural
            found = search(root, operations + [(kind, suffix)], depth + 1)
            if found:
                return found
        for root, suffix, kind in list(_candidate_strips(current, GRAMMATICAL_SUFFIXES, "grammar")) + list(_candidate_strips(current, DERIVATIONAL_SUFFIXES, "derivation")):
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
        return root[:-1] + suffix if root.endswith("ు") else root + suffix
    if kind == "derived_voice":
        return root[:-1] + suffix if root.endswith("ు") else root + suffix
    if kind == "plural":
        if suffix == "ాలు":
            return root[:-1] + "ాలు" if root.endswith("ం") else root + "లు"
        return root + "లు"
    if kind == "lexical_plural":
        return root
    if kind == "adjective":
        return root[:-1] + "మైన" if root.endswith("ం") else root + "మైన"
    if kind == "adjective_predicate":
        return root + "గా"
    if kind == "adjective_invariant":
        return root
    if kind == "bare_nominal":
        return root[:-1] if root.endswith("ం") else root
    if kind == "relational_adjective":
        return root[:-1] + "పు" if root.endswith("ం") else root + "పు"
    if kind == ACCUSATIVE or suffix == ACCUSATIVE:
        if root.endswith("లు"):
            return root + "ను"
        if root.endswith("ం"):
            return root[:-1] + "ాన్ని"
        if root.endswith("ు"):
            return root + "ను"
        return root + "ని"
    if kind == DATIVE or suffix == DATIVE:
        if root.endswith("లు"):
            return root + "కు"
        if root.endswith("ం"):
            return root[:-1] + "ానికి"
        return root + "కు"
    if kind == "grammar":
        if root.endswith("లు") and suffix in {"ను", "ని"}:
            return root + suffix
        if root.endswith("లు") and suffix in {"కు", "కి", "తో", "లో", "పై"}:
            return root + suffix
        if root.endswith("ం"):
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
