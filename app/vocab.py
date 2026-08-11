import json
import os
import re
from typing import Dict, List, Optional, Tuple

from app.config import settings


# ============================================================
# FILE HELPERS
# ============================================================

def _path(filename: str) -> str:
    return os.path.join(
        settings.DATA_DIR,
        filename,
    )


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

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def _save_json(
    filename: str,
    data,
) -> None:

    os.makedirs(
        settings.DATA_DIR,
        exist_ok=True,
    )

    with open(
        _path(filename),
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# LOAD MELIMI RESOURCES
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
# TELUGU TOKENIZATION
# ============================================================

_WORD_RE = re.compile(
    r"[\u0C00-\u0C7F\w]+",
    re.UNICODE,
)


def _tokenize(
    text: str,
) -> List[str]:

    return _WORD_RE.findall(
        text or ""
    )


def _normalize(
    value: str,
) -> str:

    value = str(
        value or ""
    ).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def _clean_for_matching(
    value: str,
) -> str:

    value = _normalize(
        value
    )

    value = re.sub(
        r"[^\u0C00-\u0C7F\w]+",
        " ",
        value,
        flags=re.UNICODE,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _contains_term(
    text: str,
    term: str,
) -> bool:

    text = _clean_for_matching(
        text
    )

    term = _clean_for_matching(
        term
    )

    if not text or not term:
        return False

    padded_text = (
        " "
        + text
        + " "
    )

    padded_term = (
        " "
        + term
        + " "
    )

    return padded_term in padded_text


# ============================================================
# SEARCHABLE ENTRY
# ============================================================

def _field_to_text(
    value,
) -> str:

    if isinstance(
        value,
        list,
    ):

        return " ".join(
            str(item)
            for item in value
        )

    if isinstance(
        value,
        dict,
    ):

        return " ".join(
            str(item)
            for item in value.values()
        )

    return str(
        value or ""
    )


def _searchable_entry_text(
    entry: Dict,
) -> str:

    fields = []

    keys = [
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

    for key in keys:

        value = _field_to_text(
            entry.get(
                key,
                "",
            )
        )

        if value:
            fields.append(
                value
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
    Retrieve the most relevant Melimi vocabulary
    for the user's message.

    The entire vocabulary.json is never sent to Groq.

    Ranking:

    1. Exact Melimi match
    2. Exact standard Telugu match
    3. Melimi token match
    4. Standard token match
    5. Meaning/definition match
    6. Related searchable fields
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

    normalized_message = _normalize(
        message
    )

    tokens = [
        _normalize(token)
        for token in _tokenize(message)
        if len(token.strip()) >= 2
    ]

    scored: List[
        Tuple[int, int, Dict]
    ] = []


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

        searchable = (
            _searchable_entry_text(
                entry
            )
        )

        score = 0


        # ----------------------------------------------------
        # EXACT MELIMI
        # ----------------------------------------------------

        if (
            melimi
            and _contains_term(
                normalized_message,
                melimi,
            )
        ):

            score += 200


        # ----------------------------------------------------
        # EXACT STANDARD
        # ----------------------------------------------------

        if (
            standard
            and _contains_term(
                normalized_message,
                standard,
            )
        ):

            score += 180


        # ----------------------------------------------------
        # TOKEN MATCHES
        # ----------------------------------------------------

        for token in tokens:

            if (
                melimi
                and token == melimi
            ):

                score += 150

            elif (
                standard
                and token == standard
            ):

                score += 130

            elif (
                token
                and token in searchable
            ):

                score += 20


        # ----------------------------------------------------
        # PARTIAL WORD MATCH
        # ----------------------------------------------------

        for token in tokens:

            if len(token) < 3:
                continue


            if (
                standard
                and token in standard
            ):

                score += 15


            if (
                melimi
                and token in melimi
            ):

                score += 18


        # ----------------------------------------------------
        # MEANING / DEFINITION
        # ----------------------------------------------------

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
                and meaning in normalized_message
            ):

                score += 80


        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

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
            and notes in normalized_message
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
# RESPONSE VOCABULARY CHECK
# ============================================================

def find_standard_melimi_alternatives(
    response: str,
    limit: int = None,
) -> List[Dict]:

    """
    Find established standard-Telugu words occurring in the
    generated response for which vocabulary.json contains
    a different Melimi form.

    Example:

        standard = "భాష"
        melimi = "నుడి"

    If the generated response contains "భాష", this function
    returns that vocabulary entry.

    This does NOT perform blind replacement.
    The result is passed to Groq so Groq can rewrite the
    complete sentence naturally.
    """

    limit = (
        limit
        or settings.MAX_RESPONSE_CHECKS
    )

    if not response:
        return []

    matches = []

    for index, entry in enumerate(
        VOCABULARY
    ):

        standard = str(
            entry.get(
                "standard",
                "",
            )
        ).strip()

        melimi = str(
            entry.get(
                "melimi",
                "",
            )
        ).strip()


        if not standard or not melimi:
            continue


        # Same word means there is no alternative.
        if _normalize(
            standard
        ) == _normalize(
            melimi
        ):
            continue


        if _contains_term(
            response,
            standard,
        ):

            # If the response already contains
            # the Melimi form too, don't force a rewrite
            # unnecessarily.
            if _contains_term(
                response,
                melimi,
            ):
                continue


            matches.append(
                (
                    len(
                        _clean_for_matching(
                            standard
                        )
                    ),
                    index,
                    entry,
                )
            )


    # Longer expressions first.
    matches.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )


    return [
        entry
        for _, _, entry
        in matches[:limit]
    ]


# ============================================================
# VOCABULARY FOR RESPONSE CHECKING
# ============================================================

def get_melimi_alternatives_for_text(
    text: str,
    limit: int = None,
) -> List[Dict]:

    return find_standard_melimi_alternatives(
        text,
        limit=limit,
    )


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

        melimi = str(
            entry.get(
                "melimi",
                "",
            )
        )

        words.update(
            _tokenize(
                melimi
            )
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

        if not re.search(
            r"[\u0C00-\u0C7F]",
            token,
        ):
            continue


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


    # --------------------------------------------------------
    # SUFFIXES
    # --------------------------------------------------------

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
            len(
                matched_suffixes
            )
            >= limit
        ):

            break


    # --------------------------------------------------------
    # PREFIXES
    # --------------------------------------------------------

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
            len(
                matched_prefixes
            )
            >= limit
        ):

            break


    # --------------------------------------------------------
    # REDUPLICATION
    # --------------------------------------------------------

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
