from __future__ import annotations

import re

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

    Crucially, lookup is root-first: an inflected source surface form is
    reduced before the authoritative source-root mapping is applied, and the
    same grammatical operation is then re-applied to the target root.
    """
    word = _extract_word(message)
    roots = language_roots()
    if not word or not roots:
        # In explicit Melimi mode, a bare registered source form is also a
        # useful lexical lookup. Unknown words remain unknown; never invent.
        if message.strip() not in roots:
            return None
        word = message.strip()
    form = reduce_to_root(word, roots)
    target = roots.get(form.root)
    if not target:
        return None
    return reapply_operations(target, form)
