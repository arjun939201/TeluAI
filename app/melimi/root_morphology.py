"""Root-first Melimi morphology with corpus-backed derivation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")
GRAMMATICAL_SUFFIXES = tuple(sorted(["లతో","లలో","లకు","లను","లని","లపై","లకై","లవల్ల","నుంచి","నుండి","యొక్క","తోటి","గురించి","కోసం","వల్ల","మధ్య","లోని","పైన","తో","లో","లు","న్ని","ాన్ని","ానికి","ను","ని","కు","కి","గా","పై","ల"], key=len, reverse=True))
VERB_SUFFIXES = tuple(sorted(["స్తుంది","స్తున్నారు","స్తున్నాను","స్తున్నావు","స్తున్నాడు","స్తున్నది","తుంది","తున్నారు","తున్నాను","తున్నావు","తున్నాడు","తున్నది","డానికి","డంలో","డాన్ని","డిగా","డుతూ","డిన","డినది","చడం","చడానికి","చడంలో","చడాన్ని","చుతూ","చిన","చింది","డం"], key=len, reverse=True))
DERIVATIONAL_SUFFIXES = tuple(sorted(["అలవి","అల్వి","అరిది","అర్ది","కాను","కాన్","మారి","వాను","వాన్","పాదు","పఱ","కము","ఇకము","మాలు","గము","ఓరు","ఆది","ఓలి","ఓజ","అంగి","ఇద","ద","అ","పు"], key=len, reverse=True))
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

def _plural_candidate(surface, roots):
    if surface.endswith("ాలు"):
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, "ాలు", "plural"
    if surface.endswith("లు"):
        candidate = surface[:-2]
        if candidate in roots: return candidate, "లు", "plural"
    return None

def _case_candidate(surface, roots):
    if surface.endswith("లను"):
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, (("case", ACCUSATIVE), ("plural", "లు"))
    if surface.endswith("లకు"):
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, (("case", DATIVE), ("plural", "లు"))
    if surface.endswith("న్ని"):
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, (("case", ACCUSATIVE),)
    if surface.endswith("ాన్ని"):
        candidate = surface[:-5] + "ం"
        if candidate in roots: return candidate, (("case", ACCUSATIVE),)
    if surface.endswith("ానికి"):
        candidate = surface[:-6] + "ం"
        if candidate in roots: return candidate, (("case", DATIVE),)
    if surface.endswith("కి"):
        stem = surface[:-2]
        if stem.endswith("ని"):
            candidate = stem[:-2] + "ం"
            if candidate in roots: return candidate, (("case", DATIVE),)
    return None

def _adjectival_candidate(surface, roots):
    if surface.endswith("మైన"):
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, "మైన", "adjective"
    if surface.endswith("గా"):
        candidate = surface[:-2] + "ం"
        if candidate in roots: return candidate, "గా", "adjective_predicate"
    if surface.endswith("ా"):
        candidate = surface[:-1]
        if candidate in roots: return candidate, "ా", "adjective_invariant"
    if surface.endswith("పు") and surface[:-2] + "ం" in roots:
        return surface[:-2] + "ం", "పు", "relational_adjective"
    return None

def _verb_candidate(surface, roots):
    for suffix in VERB_SUFFIXES:
        if surface.endswith(suffix):
            stem = surface[:-len(suffix)]
            for candidate in (stem, stem + "ు", stem + "చు"):
                if candidate in roots: return candidate, suffix, "verb"
    return None

def reduce_to_root(word, roots=None) -> MorphologicalForm:
    surface = (word or "").strip()
    roots = roots or load_root_dictionary()
    if not surface: return MorphologicalForm("", "")
    if surface in roots: return MorphologicalForm(surface, surface)
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
    adj = _adjectival_candidate(surface, roots)
    if adj:
        root, suffix, kind = adj
        return MorphologicalForm(surface, root, (suffix,), (kind,))
    for suffix in DERIVATIONAL_SUFFIXES:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            candidate = surface[:-len(suffix)]
            if candidate in roots: return MorphologicalForm(surface, candidate, (suffix,), ("derivation",))
    return MorphologicalForm(surface, surface)

def apply_operation(root, kind, suffix):
    if kind == "plural":
        return root[:-1] + "ాలు" if root.endswith("ం") else root + "లు"
    if kind == "case":
        if suffix == ACCUSATIVE:
            if root.endswith("లు"): return root[:-2] + "లను"
            if root.endswith("ం"): return root[:-1] + "ాన్ని"
            return root + ("ను" if root.endswith("ు") else "ని")
        if suffix == DATIVE:
            if root.endswith("లు"): return root[:-2] + "లకు"
            if root.endswith("ం"): return root[:-1] + "ానికి"
            return root + ("కు" if root.endswith("ు") else "కి")
    if kind == "adjective": return root[:-1] + "మైన" if root.endswith("ం") else root + "మైన"
    if kind == "adjective_predicate": return root + "గా"
    if kind == "adjective_invariant": return root
    if kind == "relational_adjective": return root[:-1] + "పు" if root.endswith("ం") else root + "పు"
    if kind == "verb": return root[:-1] + suffix if root.endswith("ు") else root + suffix
    if kind == "derivation": return root + suffix
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
