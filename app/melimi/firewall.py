from __future__ import annotations

import re
from functools import lru_cache

from app.melimi.index import build_index
from app.melimi.root_morphology import (
    load_root_dictionary,
    reduce_to_root,
    reapply_operations,
)
from app.melimi.grammar import is_non_am_ending_melimi

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
_STANDARD_KEYS = ("standard", "standard_or_source", "source_word")
_MELIMI_KEYS = ("melimi", "word", "headword")


def _as_list(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


@lru_cache(maxsize=1)
def subject_lexicon():
    forbidden = {}
    preferred = {}
    registered = set()
    adjective_capable = set()

    for source, melimi in load_root_dictionary().items():
        forbidden[source] = melimi
        preferred[source] = melimi
        registered.add(melimi)

    try:
        for doc in build_index():
            if doc.kind != "vocabulary":
                continue
            for entry in doc.entries:
                standards = []
                melimis = []
                for key in _STANDARD_KEYS:
                    standards.extend(_as_list(entry.get(key)))
                for key in _MELIMI_KEYS:
                    melimis.extend(_as_list(entry.get(key)))
                if not standards or not melimis:
                    continue

                m = melimis[0]
                registered.add(m)
                capable = (
                    entry.get("adjective_invariant") is True
                    or (
                        isinstance(entry.get("functions"), list)
                        and "adjective"
                        in [str(x).strip().lower() for x in entry.get("functions", [])]
                    )
                )
                for std in standards:
                    forbidden[std] = m
                    preferred[std] = m
                    if capable and is_non_am_ending_melimi(m):
                        adjective_capable.add((std, m))
    except Exception:
        pass

    return {
        "forbidden": forbidden,
        "preferred": preferred,
        "registered": registered,
        "adjective_capable": adjective_capable,
    }


def reload_firewall():
    subject_lexicon.cache_clear()


def _match_root(token, forbidden, adjective_capable=None):
    if not token:
        return None

    form = reduce_to_root(token, forbidden)
    if form.root in forbidden:
        melimi_root = forbidden[form.root]
        capable = (form.root, melimi_root) in (adjective_capable or set())

        # Invariant Melimi adjectives are lexical target forms.  A source
        # -మైన form maps directly to the invariant target, while a source
        # -గా predicate preserves the predicate operation on that target.
        if capable and is_non_am_ending_melimi(melimi_root):
            if form.kinds == ("adjective",):
                return form.root, "", melimi_root
            if form.kinds == ("adjective_predicate",):
                return form.root, "గా", reapply_operations(melimi_root, form)

        return (
            form.root,
            form.suffixes[-1] if form.suffixes else "",
            reapply_operations(melimi_root, form),
        )

    if token in forbidden:
        return token, "", forbidden[token]

    return None


def lexical_violations(text):
    lex = subject_lexicon()
    found = []
    seen = set()
    for token in TOKEN_RE.findall(text or ""):
        result = _match_root(token, lex["forbidden"], lex.get("adjective_capable"))
        if not result:
            continue
        root, suffix, melimi = result
        key = (token, melimi)
        if key in seen:
            continue
        seen.add(key)
        found.append({
            "source": token,
            "preferred": melimi,
            "root": root,
            "suffix": suffix,
        })
    return found


def deterministic_repair(text):
    lex = subject_lexicon()

    def replace(match):
        result = _match_root(
            match.group(0),
            lex["forbidden"],
            lex.get("adjective_capable"),
        )
        return result[2] if result else match.group(0)

    return TOKEN_RE.sub(replace, text)
