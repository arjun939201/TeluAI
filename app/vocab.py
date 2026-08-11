import json
import os
import re
from typing import Dict, List, Optional

from app.config import settings


def _path(filename: str) -> str:
    return os.path.join(settings.DATA_DIR, filename)


def _load_json(filename: str):
    path = _path(filename)
    if not os.path.exists(path):
        return [] if filename != "grammar.json" else {"prefixes": [], "suffixes": [], "reduplication": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data) -> None:
    path = _path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


VOCABULARY: List[Dict] = _load_json("vocabulary.json")
GRAMMAR: Dict = _load_json("grammar.json")
EXAMPLES: List[Dict] = _load_json("examples.json")
PHRASES: List[Dict] = _load_json("phrases.json")

# Telugu-aware "word" splitter - keeps Telugu script + digits/latin together as tokens.
_WORD_RE = re.compile(r"[\u0C00-\u0C7F\w]+", re.UNICODE)


def _tokenize(message: str) -> List[str]:
    return _WORD_RE.findall(message)


# ---------------------------------------------------------------------------
# Vocabulary lookup (static word pairs)
# ---------------------------------------------------------------------------

def retrieve_vocab(message: str, limit: int = None) -> List[Dict]:
    """Return vocabulary entries whose standard-Telugu OR melimi-Telugu word/phrase
    appears in the user's message. Matching on BOTH fields matters: if the user
    already typed a melimi word, we still want to surface its standard pairing
    (and any note) so the model has an anchor for that word's meaning/register."""
    limit = limit or settings.MAX_VOCAB_MATCHES
    matches = []
    for entry in VOCABULARY:
        standard = entry.get("standard", "")
        melimi = entry.get("melimi", "")
        if (standard and standard in message) or (melimi and melimi in message):
            matches.append(entry)
    return matches[:limit]


def get_examples(limit: int = None) -> List[Dict]:
    limit = limit or settings.MAX_EXAMPLES
    return EXAMPLES[:limit]


def get_phrases(limit: int = None) -> List[Dict]:
    limit = limit or settings.MAX_PHRASES
    return PHRASES[:limit]


# ---------------------------------------------------------------------------
# Grammar / morphology lookup
# ---------------------------------------------------------------------------

def _known_vocab_melimi_words() -> set:
    words = set()
    for entry in VOCABULARY:
        for w in _tokenize(entry.get("melimi", "")):
            words.add(w)
    return words


_KNOWN_MELIMI_WORDS = _known_vocab_melimi_words()


def find_root_candidates(message: str) -> List[str]:
    """Identify tokens in the message that look like Melimi Telugu roots worth
    generating grammar-driven variations for: Telugu-script tokens that are NOT
    already a complete, known vocabulary word (so the model should treat them as
    a root + productive suffix/prefix rather than a fixed lookup)."""
    candidates = []
    for tok in _tokenize(message):
        if not re.search(r"[\u0C00-\u0C7F]", tok):
            continue  # skip non-Telugu tokens
        if tok in _KNOWN_MELIMI_WORDS:
            continue  # already a known fixed vocabulary word, no need to derive
        candidates.append(tok)
    return candidates


def retrieve_grammar(message: str, limit: int = None) -> Dict[str, List[Dict]]:
    """Find grammar rules (prefixes/suffixes/reduplication) that are relevant to
    the user's message: either the rule's element literally appears in the
    message, OR a Telugu token in the message ends/starts with the rule's
    element (suggesting the token is ROOT + this suffix, or PREFIX + this root)."""
    limit = limit or settings.MAX_GRAMMAR_MATCHES
    tokens = _tokenize(message)

    def element_variants(raw_element: str) -> List[str]:
        # elements are sometimes given as "వాను / వాన్" or "కత్తె/కత్తియ"
        parts = re.split(r"[\/,]", raw_element)
        return [p.strip().strip("'\u200c") for p in parts if p.strip()]

    matched_suffixes = []
    for rule in GRAMMAR.get("suffixes", []):
        variants = element_variants(rule.get("suffix", ""))
        hit = False
        for v in variants:
            if not v:
                continue
            if v in message:
                hit = True
                break
            for tok in tokens:
                if len(tok) > len(v) and tok.endswith(v):
                    hit = True
                    break
            if hit:
                break
        if hit:
            matched_suffixes.append(rule)
        if len(matched_suffixes) >= limit:
            break

    matched_prefixes = []
    for rule in GRAMMAR.get("prefixes", []):
        variants = element_variants(rule.get("element", ""))
        hit = False
        for v in variants:
            if not v:
                continue
            if v in message:
                hit = True
                break
            for tok in tokens:
                if len(tok) > len(v) and tok.startswith(v):
                    hit = True
                    break
            if hit:
                break
        if hit:
            matched_prefixes.append(rule)
        if len(matched_prefixes) >= limit:
            break

    return {
        "suffixes": matched_suffixes,
        "prefixes": matched_prefixes,
        "reduplication": GRAMMAR.get("reduplication", []) if not matched_suffixes and not matched_prefixes else [],
    }


# ---------------------------------------------------------------------------
# Learning: persist newly-confirmed Melimi content back to the data files
# ---------------------------------------------------------------------------

def add_vocab_entry(standard: str, melimi: str, note: str = "") -> bool:
    """Append a new standard<->melimi word pair to vocabulary.json, skipping
    exact duplicates. Returns True if a new entry was added."""
    global VOCABULARY, _KNOWN_MELIMI_WORDS
    for e in VOCABULARY:
        if e.get("standard") == standard and e.get("melimi") == melimi:
            return False
    VOCABULARY.append({"standard": standard, "melimi": melimi, "note": note})
    _save_json("vocabulary.json", VOCABULARY)
    _KNOWN_MELIMI_WORDS = _known_vocab_melimi_words()
    return True


def add_grammar_rule(kind: str, element: str, meaning: str, examples: Optional[List[str]] = None,
                      note: str = "") -> bool:
    """Append a new prefix/suffix/reduplication rule to grammar.json."""
    global GRAMMAR
    if kind not in ("prefixes", "suffixes", "reduplication"):
        raise ValueError("kind must be one of: prefixes, suffixes, reduplication")

    key = "suffix" if kind == "suffixes" else ("element" if kind == "prefixes" else "pattern")
    bucket = GRAMMAR.setdefault(kind, [])
    for e in bucket:
        if e.get(key) == element:
            return False

    entry = {key: element, "meaning": meaning, "examples": examples or []}
    if note:
        entry["note"] = note
    bucket.append(entry)
    _save_json("grammar.json", GRAMMAR)
    return True


def add_phrase(standard: str, melimi: str) -> bool:
    """Append a confirmed sentence/phrase-level translation to phrases.json."""
    global PHRASES
    for e in PHRASES:
        if e.get("standard") == standard and e.get("melimi") == melimi:
            return False
    PHRASES.append({"standard": standard, "melimi": melimi})
    _save_json("phrases.json", PHRASES)
    return True
