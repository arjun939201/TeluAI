"""Root-first Melimi morphology with corpus-backed derivation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")
GRAMMATICAL_SUFFIXES = tuple(sorted([
    "ాలతో", "ాలలో", "ాలకు", "ాలను", "ాలని", "ాలపై", "ాలకై", "ాలవల్ల",
    "లతో", "లలో", "లకు", "లను", "లని", "లపై", "లకై", "లవల్ల",
    "నుంచి", "నుండి", "యొక్క", "తోటి", "గురించి", "కోసం", "వల్ల", "మధ్య",
    "లోని", "పైన", "తో", "లో", "లు", "న్ని", "ాన్ని", "ానికి", "ను", "ని",
    "కు", "కి", "గా", "పై", "ల",
], key=len, reverse=True))
VERB_SUFFIXES = tuple(sorted([
    "స్తుంది", "స్తున్నారు", "స్తున్నాను", "స్తున్నావు", "స్తున్నాడు", "స్తున్నది",
    "తుంది", "తున్నారు", "తున్నాను", "తున్నావు", "తున్నాడు", "తున్నది",
    "డానికి", "డంలో", "డాన్ని", "డిగా", "డుతూ", "డిన", "డినది", "చడం",
    "చడానికి", "చడంలో", "చడాన్ని", "చుతూ", "చిన", "చింది", "డం",
], key=len, reverse=True))
DERIVED_VOICE_SUFFIXES = tuple(sorted(["బడిన", "బడింది", "బడే", "బడుతుంది", "బడుతున్న", "బడుతూ"], key=len, reverse=True))
DERIVATIONAL_SUFFIXES = tuple(sorted([
    "అలవి", "అల్వి", "అరిది", "అర్ది", "కాను", "కాన్", "మారి", "వాను", "వాన్",
    "పాదు", "పఱ", "కము", "ఇకము", "మాలు", "గము", "ఓరు", "ఆది", "ఓలి", "ఓజ",
    "అంగి", "ఇద", "ద", "అ", "పు",
], key=len, reverse=True))
ACCUSATIVE = "ACCUSATIVE"
DATIVE = "DATIVE"
INSTRUMENTAL = "INSTRUMENTAL"
LOCATIVE = "LOCATIVE"
OBLIQUE = "OBLIQUE"

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

def _known_candidate(candidates, roots):
    for candidate in candidates:
        if candidate in roots:
            return candidate
    return None

def _plural_candidate(surface, roots):
    for suffix in ("ాలు", "లు"):
        if surface.endswith(suffix):
            base = surface[:-len(suffix)]
            candidate = _known_candidate((base, base + "ం"), roots)
            if candidate:
                return candidate, suffix, "plural"
    return None

def _case_candidate(surface, roots):
    # Analyze plural case as two abstract operations: plural + case.
    # This supports both -లు- stems and -ాలు- stems.
    plural_cases = {
        "ాలను": ACCUSATIVE, "ాలని": ACCUSATIVE,
        "ాలకు": DATIVE, "ాలకై": DATIVE,
        "ాలతో": INSTRUMENTAL, "ాలలో": LOCATIVE,
        "ాలపై": LOCATIVE, "ాలవల్ల": OBLIQUE,
        "లను": ACCUSATIVE, "లని": ACCUSATIVE,
        "లకు": DATIVE, "లకై": DATIVE,
        "లతో": INSTRUMENTAL, "లలో": LOCATIVE,
        "లపై": LOCATIVE, "లవల్ల": OBLIQUE, "ల": OBLIQUE,
    }
    for suffix, case_name in sorted(plural_cases.items(), key=lambda item: len(item[0]), reverse=True):
        if not surface.endswith(suffix):
            continue
        base = surface[:-len(suffix)]
        candidate = _known_candidate((base, base + "ం"), roots)
        if candidate:
            return candidate, (("case", case_name), ("plural", "లు"))

    # AM-final singular case sandhi.
    for surface_suffix, case_name in (("ాన్ని", ACCUSATIVE), ("ానికి", DATIVE)):
        if surface.endswith(surface_suffix):
            candidate = surface[:-len(surface_suffix)] + "ం"
            if candidate in roots:
                return candidate, (("case", case_name),)

    singular_cases = {
        "ను": ACCUSATIVE, "కు": DATIVE, "కి": DATIVE,
        "తో": INSTRUMENTAL, "లో": LOCATIVE, "పై": LOCATIVE,
    }
    for suffix, case_name in sorted(singular_cases.items(), key=lambda item: len(item[0]), reverse=True):
        if surface.endswith(suffix):
            base = surface[:-len(suffix)]
            candidate = _known_candidate((base, base + "ం"), roots)
            if candidate:
                return candidate, (("case", case_name),)

    if surface.endswith("న్ని"):
        base = surface[:-3]
        candidate = _known_candidate((base, base + "ం"), roots)
        if candidate:
            return candidate, (("case", ACCUSATIVE),)
    return None

def _adjectival_candidate(surface, roots):
    if surface.endswith("మైన"):
        candidate = surface[:-3] + "ం"
        if candidate in roots:
            return candidate, "మైన", "adjective"
    if surface.endswith("గా"):
        candidate = surface[:-2] + "ం"
        if candidate in roots:
            return candidate, "గా", "adjective_predicate"
    if surface + "ం" in roots:
        return surface + "ం", "BARE_AM", "bare_nominal"
    if surface.endswith("ా"):
        candidate = surface[:-1]
        if candidate in roots:
            return candidate, "ా", "adjective_invariant"
    if surface.endswith("పు") and surface[:-2] + "ం" in roots:
        return surface[:-2] + "ం", "పు", "relational_adjective"
    return None

def _verb_candidate(surface, roots):
    for suffix in VERB_SUFFIXES:
        if surface.endswith(suffix):
            stem = surface[:-len(suffix)]
            for candidate in (stem, stem + "ు", stem + "చు"):
                if candidate in roots:
                    return candidate, suffix, "verb"
    return None

def _derived_voice_candidate(surface, roots):
    for suffix in DERIVED_VOICE_SUFFIXES:
        if surface.endswith(suffix):
            stem = surface[:-len(suffix)]
            if stem.endswith("ించ"):
                candidate = stem[:-3] + "నం"
                if candidate in roots:
                    return candidate, suffix, "derived_voice"
    return None

def reduce_to_root(word, roots=None) -> MorphologicalForm:
    surface = (word or "").strip()
    roots = roots or load_root_dictionary()
    if not surface:
        return MorphologicalForm("", "")
    if surface in roots:
        return MorphologicalForm(surface, surface)
    case = _case_candidate(surface, roots)
    if case:
        root, ops = case
        return MorphologicalForm(surface, root, tuple(x[1] for x in ops), tuple(x[0] for x in ops))
    plural = _plural_candidate(surface, roots)
    if plural:
        root, suffix, kind = plural
        return MorphologicalForm(surface, root, (suffix,), (kind,))
    verb = _verb_candidate(surface, roots)
    if verb:
        root, suffix, kind = verb
        return MorphologicalForm(surface, root, (suffix,), (kind,))
    voice = _derived_voice_candidate(surface, roots)
    if voice:
        root, suffix, kind = voice
        return MorphologicalForm(surface, root, (suffix,), (kind,))
    adj = _adjectival_candidate(surface, roots)
    if adj:
        root, suffix, kind = adj
        return MorphologicalForm(surface, root, (suffix,), (kind,))
    for suffix in DERIVATIONAL_SUFFIXES:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            candidate = surface[:-len(suffix)]
            if candidate in roots:
                return MorphologicalForm(surface, candidate, (suffix,), ("derivation",))
    return MorphologicalForm(surface, surface)

def apply_operation(root, kind, suffix):
    if kind == "plural":
        if root.endswith("ం"):
            return root[:-1] + "ాలు"
        return root + "లు"
    if kind == "case":
        if suffix == ACCUSATIVE:
            if root.endswith("లు"):
                return root[:-1] + "ను"
            if root.endswith("ం"):
                return root[:-1] + "ాన్ని"
            if root.endswith("ా"):
                return root + "ను"
            if root.endswith("ు"):
                return root + "ను"
            return root + "ని"
        if suffix == DATIVE:
            if root.endswith("లు"):
                return root[:-1] + "కు"
            if root.endswith("ం"):
                return root[:-1] + "ానికి"
            if root.endswith("ా"):
                return root + "కు"
            if root.endswith("ు") or root.endswith("ి"):
                return root + "కు"
            return root + "కి"
        if suffix == INSTRUMENTAL:
            if root.endswith("లు"):
                return root[:-1] + "తో"
            return root + "తో"
        if suffix == LOCATIVE:
            if root.endswith("లు"):
                return root[:-1] + "లో"
            return root + "లో"
        if suffix == OBLIQUE:
            if root.endswith("లు"):
                return root[:-1]
            if root.endswith("ు"):
                return root[:-1]
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
    if kind == "verb":
        return root[:-1] + suffix if root.endswith("ు") else root + suffix
    if kind == "derived_voice":
        return root[:-1] + suffix if root.endswith("ు") else root + suffix
    if kind == "derivation":
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
    if form.root not in roots:
        return word
    return reapply_operations(roots[form.root], form)

def convert_text(text, roots=None):
    roots = roots or load_root_dictionary()
    return TELUGU_RE.sub(lambda m: convert_surface(m.group(0), roots), text or "")
