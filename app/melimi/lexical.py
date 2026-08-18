from __future__ import annotations

import re

from app.melimi import main_dictionary
from app.melimi.db_subject import language_roots
from app.melimi.root_morphology import reduce_to_root, reapply_operations

_LOOKUP_RE = re.compile(
    r"^\s*(?P<word>[\u0C00-\u0C7F]+)\s*(?:=|→|->|—)\s*$"
    r"|^\s*(?P<word2>[\u0C00-\u0C7F]+)\s*(?:కి|కు|యొక్క)?\s*(?:మేలిమి|మెలిమి)\s*(?:తెలుగు\s*)?(?:పదం|రూపం|equivalent)?\s*(?:ఏమిటి|ఏమంటారు|ఏమిటో|ఏది|ఏమి)?\s*[?？.]?\s*$"
    r"|^\s*(?:మేలిమి|మెలిమి)\s*(?:తెలుగు\s*)?(?:లో\s*)?(?:పదం|రూపం)\s*(?:ఏమిటి|ఏమంటారు)?\s*[:：-]?\s*(?P<word3>[\u0C00-\u0C7F]+)\s*[?？.]?\s*$",
    re.I,
)


def _extract_word(message: str) -> str | None:
    m = _LOOKUP_RE.match(message or "")
    if not m:
        return None
    return (m.group("word") or m.group("word2") or m.group("word3") or "").strip() or None


def direct_lookup(message: str) -> str | None:
    """Resolve a direct source-form → Melimi lookup deterministically.

    Lookup is root-first and authority-aware. Main-dictionary entries are
    checked first after morphological reduction; older Language Space roots
    are only a fallback. This prevents a stale/user root from shadowing the
    declared main dictionary source.
    """
    word = _extract_word(message)
    roots = language_roots()
    if not word or not roots:
        if message.strip() not in roots:
            return None
        word = message.strip()

    form = reduce_to_root(word, roots)

    # The main dictionary is the highest lexical authority. The lookup is
    # deliberately performed after reduction so an inflected source form can
    # resolve to its authoritative lemma and retain its grammatical operation.
    authoritative = main_dictionary.lookup(form.root)
    if authoritative:
        target = authoritative.get("melimi_form")
        if target:
            return reapply_operations(target, form)

    target = roots.get(form.root)
    if not target:
        return None
    return reapply_operations(target, form)
