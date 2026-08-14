
from __future__ import annotations
import re
from functools import lru_cache
from app.melimi.index import build_index

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")

# Accepted field-name aliases in a vocabulary entry, so richer/varied source
# data (synonym lists, alternate key names) is still picked up. This is a
# deterministic, file-derived list only — it never invents a mapping.
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
    for doc in build_index():
        if doc.kind != "vocabulary":
            continue
        for entry in doc.entries:
            standards = []
            for key in _STANDARD_KEYS:
                standards.extend(_as_list(entry.get(key)))
            melimis = []
            for key in _MELIMI_KEYS:
                melimis.extend(_as_list(entry.get(key)))
            if not standards or not melimis:
                continue
            # The canonical Melimi form is the first supplied one; any
            # additional standard-side variants (synonyms) all map to it.
            m = melimis[0]
            registered.add(m)
            for s in standards:
                forbidden[s] = m
                preferred[s] = m
    return {"forbidden": forbidden, "preferred": preferred, "registered": registered}


def reload_firewall():
    subject_lexicon.cache_clear()


def _sorted_sources(lex):
    # Longest source words first, so e.g. a mapped compound word is matched
    # before a shorter mapped word that happens to be its substring.
    return sorted(lex["forbidden"].items(), key=lambda kv: len(kv[0]), reverse=True)


def lexical_violations(text: str):
    lex = subject_lexicon()
    found = []
    for source, melimi in _sorted_sources(lex):
        if re.search(rf"(?<![\u0C00-\u0C7F]){re.escape(source)}(?![\u0C00-\u0C7F])", text):
            found.append({"source": source, "preferred": melimi})
    return found


def deterministic_repair(text: str):
    """Final safety net for exact lexical items explicitly defined by files.

    This performs targeted, word-level substitution only: each matched
    Standard-Telugu word is swapped for its registered Melimi form in place,
    leaving the rest of the sentence (grammar, word order, every other word)
    completely untouched. It is deliberately limited to exact source-side
    vocabulary entries from the authoritative subject — it never rewrites,
    reorders, or regenerates the sentence, and it is not a general
    word-replacement engine.
    """
    out = text
    lex = subject_lexicon()
    for source, melimi in _sorted_sources(lex):
        out = re.sub(
            rf"(?<![\u0C00-\u0C7F]){re.escape(source)}(?![\u0C00-\u0C7F])",
            melimi,
            out,
        )
    return out
