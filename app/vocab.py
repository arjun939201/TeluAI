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
        if filename == "grammar.json":
            return {
                "prefixes": [],
                "suffixes": [],
                "reduplication": [],
            }

        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data) -> None:
    path = _path(filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# LOAD MELIMI LANGUAGE DATA
# ============================================================

VOCABULARY: List[Dict] = _load_json(
    "vocabulary.json"
)

GRAMMAR: Dict = _load_json(
    "grammar.json"
)

EXAMPLES: List[Dict] = _load_json(
    "examples.json"
)

PHRASES: List[Dict] = _load_json(
    "phrases.json"
)


# ============================================================
# TELUGU TOKENIZER
# ============================================================

_WORD_RE = re.compile(
    r"[\u0C00-\u0C7F\w]+",
    re.UNICODE,
)


def _tokenize(message: str) -> List[str]:

    return _WORD_RE.findall(
        message or ""
    )


def _normalize(value: str) -> str:

    value = str(
        value or ""
    ).strip().lower()

    return re.sub(
        r"\s+",
        " ",
        value,
    )


# ============================================================
# BUILD SEARCHABLE VOCABULARY TEXT
# ============================================================

def _searchable_entry_text(
    entry: Dict,
) -> str:

    fields = []

    possible_fields = [
        "standard",
        "melimi",
        "meaning",
        "definition",
        "english",
        "note",
        "notes",
        "description",
        "gloss",
        "example",
        "examples",
        "related",
        "synonyms",
        "tags",
    ]

    for key in possible_fields:

        value = entry.get(
            key,
            "",
        )

        if isinstance(
            value,
            list,
        ):
            value = " ".join(
                str(item)
                for item in value
            )

        elif isinstance(
            value,
            dict,
        ):
            value = " ".join(
                str(item)
                for item in value.values()
            )

        if value:

            fields.append(
                str(value)
            )

    return _normalize(
        " ".join(fields)
    )


# ============================================================
# VOCABULARY RETRIEVAL
# ============================================================

def retrieve_vocab(
    message: str,
    limit: int = None,
) -> List[Dict]:
    """
    Retrieve the most relevant Melimi Telugu vocabulary.

    The entire vocabulary.json is NEVER sent to Groq.

    Instead, entries are ranked according to relevance.

    Priority:

    1. Exact Melimi match
    2. Exact standard Telugu match
    3. Melimi token match
    4. Standard Telugu token match
    5. Meaning/definition match
    6. Related searchable information
    """

    limit = (
        limit
        or settings.MAX_VOCAB_MATCHES
    )

    message = (
        message
        or ""
    ).strip()

    if not message:
        return []

    message_normalized = _normalize(
        message
    )

    tokens = [
        _normalize(token)
        for token in _tokenize(message)
        if len(token.strip()) >= 2
    ]

    scored = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standard = _normalize(
            entry.get(
                "standard",
                "",
            )
        )

        melimi = _normalize(
            entry.get(
                "melimi",
                "",
            )
        )

        searchable = _searchable_entry_text(
            entry
        )

        score = 0


        # ====================================================
        # EXACT MELIMI MATCH
        # ====================================================

        if (
            melimi
            and melimi in message_normalized
        ):
            score += 150


        # ====================================================
        # EXACT STANDARD TELUGU MATCH
        # ====================================================

        if (
            standard
            and standard in message_normalized
        ):
            score += 130


        # ====================================================
        # TOKEN MATCHING
        # ====================================================

        for token in tokens:

            if (
                melimi
                and token == melimi
            ):
                score += 120

            elif (
                standard
                and token == standard
            ):
                score += 100

            elif (
                token
                and token in searchable
            ):
                score += 20


        # ====================================================
        # PARTIAL MATCH
        # ====================================================

        for token in tokens:

            if len(token) < 3:
                continue


            if (
                standard
                and token in standard
            ):
                score += 12


            if (
                melimi
                and token in melimi
            ):
                score += 15


        # ====================================================
        # MEANING / DEFINITION MATCH
        # ====================================================

        meaning_fields = [
            entry.get(
                "meaning",
                "",
            ),

            entry.get(
                "definition",
                "",
            ),

            entry.get(
                "english",
                "",
            ),
        ]


        for meaning in meaning_fields:

            meaning = _normalize(
                meaning
            )

            if (
                meaning
                and meaning in message_normalized
            ):
                score += 80


        # ====================================================
        # NOTE / DESCRIPTION MATCH
        # ====================================================

        notes = _normalize(
            entry.get(
                "note",
                entry.get(
                    "notes",
                    entry.get(
                        "description",
                        "",
                    ),
                ),
            )
        )

        if (
            notes
            and notes in message_normalized
        ):
            score += 30


        if score > 0:

            scored.append(
                (
                    score,
                    index,
                    entry,
                )
            )


    # Highest relevance first
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )


    return [
        entry
        for _, _, entry
        in scored[:limit]
    ]


# ============================================================
# EXAMPLES
# ============================================================

def get_examples(
    limit: int = None,
) -> List[Dict]:

    limit = (
        limit
        or settings.MAX_EXAMPLES
    )

    return EXAMPLES[:limit]


# ============================================================
# PHRASES
# ============================================================

def get_phrases(
    limit: int = None,
) -> List[Dict]:

    limit = (
        limit
        or settings.MAX_PHRASES
    )

    return PHRASES[:limit]


# ============================================================
# KNOWN MELIMI WORDS
# ============================================================

def _known_vocab_melimi_words() -> set:

    words = set()

    for entry in VOCABULARY:

        melimi = entry.get(
            "melimi",
            "",
        )

        words.update(
            _tokenize(melimi)
        )

    return words


_KNOWN_MELIMI_WORDS = (
    _known_vocab_melimi_words()
)


# ============================================================
# ROOT CANDIDATES
# ============================================================

def find_root_candidates(
    message: str,
) -> List[str]:

    candidates = []

    for token in _tokenize(
        message
    ):

        # Only Telugu-script words
        if not re.search(
            r"[\u0C00-\u0C7F]",
            token,
        ):
            continue


        # Already known vocabulary
        # does not need root analysis.
        if token in _KNOWN_MELIMI_WORDS:
            continue


        candidates.append(
            token
        )


    return candidates


# ============================================================
# GRAMMAR RETRIEVAL
# ============================================================

def retrieve_grammar(
    message: str,
    limit: int = None,
) -> Dict[str, List[Dict]]:

    limit = (
        limit
        or settings.MAX_GRAMMAR_MATCHES
    )

    tokens = _tokenize(
        message
    )


    def element_variants(
        raw_element: str,
    ) -> List[str]:

        parts = re.split(
            r"[/,]",
            str(
                raw_element
                or ""
            ),
        )

        return [
            part.strip()
            .strip(
                "'\u200c"
            )
            for part in parts
            if part.strip()
        ]


    # ========================================================
    # SUFFIXES
    # ========================================================

    matched_suffixes = []

    for rule in GRAMMAR.get(
        "suffixes",
        [],
    ):

        variants = element_variants(
            rule.get(
                "suffix",
                "",
            )
        )

        hit = False


        for variant in variants:

            if not variant:
                continue


            if variant in message:

                hit = True
                break


            for token in tokens:

                if (
                    len(token)
                    > len(variant)
                    and token.endswith(
                        variant
                    )
                ):

                    hit = True
                    break


            if hit:
                break


        if hit:

            matched_suffixes.append(
                rule
            )


        if (
            len(matched_suffixes)
            >= limit
        ):
            break


    # ========================================================
    # PREFIXES
    # ========================================================

    matched_prefixes = []

    for rule in GRAMMAR.get(
        "prefixes",
        [],
    ):

        variants = element_variants(
            rule.get(
                "element",
                "",
            )
        )

        hit = False


        for variant in variants:

            if not variant:
                continue


            if variant in message:

                hit = True
                break


            for token in tokens:

                if (
                    len(token)
                    > len(variant)
                    and token.startswith(
                        variant
                    )
                ):

                    hit = True
                    break


            if hit:
                break


        if hit:

            matched_prefixes.append(
                rule
            )


        if (
            len(matched_prefixes)
            >= limit
        ):
            break


    # ========================================================
    # REDUPLICATION
    # ========================================================

    matched_reduplication = []

    for rule in GRAMMAR.get(
        "reduplication",
        [],
    ):

        pattern = str(
            rule.get(
                "pattern",
                "",
            )
        )

        if (
            pattern
            and pattern in message
        ):

            matched_reduplication.append(
                rule
            )


        if (
            len(
                matched_reduplication
            )
            >= limit
        ):
            break


    return {
        "suffixes":
            matched_suffixes,

        "prefixes":
            matched_prefixes,

        "reduplication":
            matched_reduplication,
    }


# ============================================================
# LEARNING
# ============================================================

def add_vocab_entry(
    standard: str,
    melimi: str,
    note: str = "",
) -> bool:

    global VOCABULARY
    global _KNOWN_MELIMI_WORDS


    for entry in VOCABULARY:

        if (
            entry.get(
                "standard"
            )
            == standard
            and
            entry.get(
                "melimi"
            )
            == melimi
        ):

            return False


    VOCABULARY.append(
        {
            "standard":
                standard,

            "melimi":
                melimi,

            "note":
                note,
        }
    )


    _save_json(
        "vocabulary.json",
        VOCABULARY,
    )


    _KNOWN_MELIMI_WORDS = (
        _known_vocab_melimi_words()
    )


    return True


def add_grammar_rule(
    kind: str,
    element: str,
    meaning: str,
    examples: Optional[
        List[str]
    ] = None,
    note: str = "",
) -> bool:

    global GRAMMAR


    if kind not in (
        "prefixes",
        "suffixes",
        "reduplication",
    ):

        raise ValueError(
            "kind must be one of: "
            "prefixes, suffixes, "
            "reduplication"
        )


    key = (
        "suffix"
        if kind == "suffixes"
        else (
            "element"
            if kind == "prefixes"
            else "pattern"
        )
    )


    bucket = GRAMMAR.setdefault(
        kind,
        [],
    )


    for entry in bucket:

        if entry.get(
            key
        ) == element:

            return False


    entry = {
        key:
            element,

        "meaning":
            meaning,

        "examples":
            examples or [],
    }


    if note:

        entry["note"] = note


    bucket.append(
        entry
    )


    _save_json(
        "grammar.json",
        GRAMMAR,
    )


    return True


def add_phrase(
    standard: str,
    melimi: str,
) -> bool:

    global PHRASES


    for entry in PHRASES:

        if (
            entry.get(
                "standard"
            )
            == standard
            and
            entry.get(
                "melimi"
            )
            == melimi
        ):

            return False


    PHRASES.append(
        {
            "standard":
                standard,

            "melimi":
                melimi,
        }
    )


    _save_json(
        "phrases.json",
        PHRASES,
    )


    return True
