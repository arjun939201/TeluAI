"""Generic root-first Melimi morphology backed by Language Space."""
from __future__ import annotations
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Optional, Tuple

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")
GRAMMATICAL_SUFFIXES = tuple(sorted([
    "లతో","లలో","లకు","లను","లని","లపై","లకై","లవల్ల","నుంచి","నుండి","యొక్క",
    "తోటి","గురించి","కోసం","వల్ల","మధ్య","లోని","పైన","తో","లో","లు","ను","ని",
    "కు","కి","గా","పై","ల",
], key=len, reverse=True))
DERIVATIONAL_SUFFIXES = tuple(sorted([
    "అలవి","అల్వి","అరిది","అర్ది","కాను","కాన్","మారి","వాను","వాన్","పాదు","పఱ",
    "కము","ఇకము","మాలు","గము","ఓరు","ఆది","ఓలి","ఓజ","అంగి","ఇద","ద","అ",
], key=len, reverse=True))

@dataclass(frozen=True)
class MorphologicalForm:
    surface: str
    root: str
    suffixes: Tuple[str,...] = ()
    kinds: Tuple[str,...] = ()
    @property
    def operations(self): return tuple(zip(self.kinds, self.suffixes))

@lru_cache(maxsize=1)
def load_root_dictionary() -> Dict[str,str]:
    try:
        from app.melimi.db_subject import language_roots
        return language_roots()
    except Exception:
        return {}

def reload_root_dictionary(): load_root_dictionary.cache_clear()

def _candidate_strips(surface: str, suffixes: Iterable[str], kind: str):
    for suffix in suffixes:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            yield surface[:-len(suffix)], suffix, kind

def _adjectival_candidate(surface: str, roots: Dict[str,str]):
    if surface.endswith("మైన") and len(surface) > 4:
        candidate = surface[:-3] + "ం"
        if candidate in roots: return candidate, "మైన", "adjective"
    if surface.endswith("ా") and len(surface) > 2:
        candidate = surface[:-1]
        if candidate in roots: return candidate, "ా", "adjective"
    return None

def reduce_to_root(word: str, roots: Optional[Dict[str,str]]=None) -> MorphologicalForm:
    surface = (word or "").strip()
    if not surface: return MorphologicalForm("", "")
    roots = roots or load_root_dictionary()
    if surface in roots: return MorphologicalForm(surface, surface)
    adj = _adjectival_candidate(surface, roots)
    if adj: return MorphologicalForm(surface, adj[0], (adj[1],), (adj[2],))
    def search(current, operations, depth):
        if current in roots: return current, operations
        if depth >= 3: return None
        candidates = list(_candidate_strips(current, GRAMMATICAL_SUFFIXES, "grammar")) + list(_candidate_strips(current, DERIVATIONAL_SUFFIXES, "derivation"))
        candidates.sort(key=lambda x: (-len(x[1]), x[0]))
        for root, suffix, kind in candidates:
            found = search(root, operations + [(kind, suffix)], depth + 1)
            if found: return found
        return None
    found = search(surface, [], 0)
    if not found: return MorphologicalForm(surface, surface)
    root, ops = found
    return MorphologicalForm(surface, root, tuple(s for _, s in ops), tuple(k for k, _ in ops))

def apply_operation(root: str, kind: str, suffix: str) -> str:
    if suffix in {"ా", "మైన"} and kind == "adjective": return root
    if root.endswith("ం") and kind == "grammar":
        stem = root[:-1] + "ా"
        forms = {"లు": stem+"లు", "ల": stem+"ల", "లను": stem+"లను", "లని": stem+"లని", "లకు": stem+"లకు", "లకై": stem+"లకై", "లపై": stem+"లపై", "లతో": stem+"లతో", "లలో": stem+"లలో"}
        if suffix in forms: return forms[suffix]
        if suffix in {"లో","తో","గా","పై"}: return root + suffix
        if suffix in {"కు","కి"}: return stem + "నికి"
        if suffix == "ను": return stem + "ను"
    return root + suffix

def reapply_operations(melimi_root: str, form: MorphologicalForm) -> str:
    result = melimi_root
    for kind, suffix in reversed(form.operations):
        result = apply_operation(result, kind, suffix)
    return result

def convert_surface(word: str, roots: Optional[Dict[str,str]]=None) -> str:
    roots = roots or load_root_dictionary()
    form = reduce_to_root(word, roots)
    if form.root not in roots: return word
    return reapply_operations(roots[form.root], form)

def convert_text(text: str, roots: Optional[Dict[str,str]]=None) -> str:
    roots = roots or load_root_dictionary()
    return TELUGU_RE.sub(lambda m: convert_surface(m.group(0), roots), text or "")
