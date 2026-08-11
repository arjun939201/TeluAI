import json
import os
import re
from typing import Dict, List, Optional

from app.config import settings


# ============================================================
# FILE HELPERS
# ============================================================

def _path(
    filename: str,
) -> str:

    return os.path.join(
        settings.DATA_DIR,
        filename,
    )


def _load_json(
    filename: str,
):

    path = _path(
        filename
    )


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
# DATA
# ============================================================

VOCABULARY = _load_json(
    "vocabulary.json"
)

GRAMMAR = _load_json(
    "grammar.json"
)

EXAMPLES = _load_json(
    "examples.json"
)

PHRASES = _load_json(
    "phrases.json"
)


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
        .strip()
        .lower(),
    )


def _split_alternatives(
    value: str,
) -> List[str]:

    """
    Supports dictionary entries such as:

        "swantham, sontham"

        "స్వంతం, సొంతం"

        "స్వంతం / సొంతం"

        "స్వంతం; సొంతం"
    """

    if not value:
        return []


    parts = re.split(
        r"\s*(?:,|/|;|\|| లేదా )\s*",
        str(value),
    )


    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def _entry_standard_forms(
    entry: Dict,
) -> List[str]:

    return _split_alternatives(
        str(
            entry.get(
                "standard",
                "",
            )
        )
    )


def _entry_melimi_forms(
    entry: Dict,
) -> List[str]:

    return _split_alternatives(
        str(
            entry.get(
                "melimi",
                "",
            )
        )
    )


def _contains_term(
    text: str,
    term: str,
) -> bool:

    text = _normalize(
        text
    )

    term = _normalize(
        term
    )


    if not text or not term:
        return False


    return (
        term in text
    )


# ============================================================
# TOKENIZATION
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


# ============================================================
# SEARCHABLE TEXT
# ============================================================

def _field_to_text(
    value,
) -> str:

    if isinstance(
        value,
        list,
    ):

        return " ".join(
            str(x)
            for x in value
        )


    if isinstance(
        value,
        dict,
    ):

        return " ".join(
            str(x)
            for x in value.values()
        )


    return str(
        value or ""
    )


def _searchable_entry_text(
    entry: Dict,
) -> str:

    fields = []

    for key in [
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
    ]:

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

    limit = (
        limit
        or settings.MAX_VOCAB_MATCHES
    )


    if not message:
        return []


    message_normalized = _normalize(
        message
    )


    tokens = [
        _normalize(x)
        for x in _tokenize(
            message
        )
    ]


    scored = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standard_forms = (
            _entry_standard_forms(
                entry
            )
        )

        melimi_forms = (
            _entry_melimi_forms(
                entry
            )
        )


        searchable = (
            _searchable_entry_text(
                entry
            )
        )


        score = 0


        # ----------------------------------------------------
        # STANDARD ALTERNATIVES
        # ----------------------------------------------------

        for standard in standard_forms:

            if _contains_term(
                message_normalized,
                standard,
            ):

                score += 180


            for token in tokens:

                if (
                    token
                    == _normalize(
                        standard
                    )
                ):

                    score += 140


        # ----------------------------------------------------
        # MELIMI FORMS
        # ----------------------------------------------------

        for melimi in melimi_forms:

            if _contains_term(
                message_normalized,
                melimi,
            ):

                score += 200


            for token in tokens:

                if (
                    token
                    == _normalize(
                        melimi
                    )
                ):

                    score += 150


        # ----------------------------------------------------
        # SEARCHABLE MEANING
        # ----------------------------------------------------

        for token in tokens:

            if (
                len(token) >= 3
                and token in searchable
            ):

                score += 15


        # ----------------------------------------------------
        # ENGLISH / MEANING
        # ----------------------------------------------------

        for key in [
            "meaning",
            "definition",
            "english",
        ]:

            value = _normalize(
                entry.get(
                    key,
                    "",
                )
            )


            if (
                value
                and value in message_normalized
            ):

                score += 70


        if score:

            scored.append(
                (
                    score,
                    index,
                    entry,
                )
            )


    scored.sort(
        key=lambda x: (
            -x[0],
            x[1],
        )
    )


    return [
        entry
        for _, _, entry
        in scored[:limit]
    ]


# ============================================================
# RESPONSE CHECKER
# ============================================================

def find_standard_melimi_alternatives(
    response: str,
    limit: int = None,
) -> List[Dict]:

    limit = (
        limit
        or settings.MAX_RESPONSE_CHECKS
    )


    matches = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standard_forms = (
            _entry_standard_forms(
                entry
            )
        )

        melimi_forms = (
            _entry_melimi_forms(
                entry
            )
        )


        if not standard_forms:
            continue

        if not melimi_forms:
            continue


        for standard in standard_forms:

            if not _contains_term(
                response,
                standard,
            ):

                continue


            # If any Melimi equivalent is already
            # present, don't force correction.
            already_melimi = any(
                _contains_term(
                    response,
                    melimi,
                )
                for melimi
                in melimi_forms
            )


            if already_melimi:
                continue


            matches.append(
                (
                    len(
                        standard
                    ),
                    index,
                    entry,
                )
            )

            break


    matches.sort(
        key=lambda x: (
            -x[0],
            x[1],
        )
    )


    return [
        entry
        for _, _, entry
        in matches[:limit]
    ]


# ============================================================
# GRAMMAR
# ============================================================

def retrieve_grammar(
    message: str,
    limit: int = None,
) -> Dict:

    limit = (
        limit
        or settings.MAX_GRAMMAR_MATCHES
    )


    tokens = _tokenize(
        message
    )


    matched_suffixes = []
    matched_prefixes = []
    matched_reduplication = []


    # --------------------------------------------------------
    # SUFFIXES
    # --------------------------------------------------------

    for rule in GRAMMAR.get(
        "suffixes",
        [],
    ):

        suffix = str(
            rule.get(
                "suffix",
                "",
            )
        )


        variants = _split_alternatives(
            suffix
        )


        found = False


        for variant in variants:

            if variant in message:

                found = True
                break


            for token in tokens:

                if token.endswith(
                    variant
                ):

                    found = True
                    break


            if found:
                break


        if found:

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

    for rule in GRAMMAR.get(
        "prefixes",
        [],
    ):

        element = str(
            rule.get(
                "element",
                "",
            )
        )


        variants = _split_alternatives(
            element
        )


        found = False


        for variant in variants:

            if variant in message:

                found = True
                break


            for token in tokens:

                if token.startswith(
                    variant
                ):

                    found = True
                    break


            if found:
                break


        if found:

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
# EXAMPLES / PHRASES
# ============================================================

def get_examples(
    limit: int = None,
) -> List[Dict]:

    return EXAMPLES[
        :(
            limit
            or settings.MAX_EXAMPLES
        )
    ]


def get_phrases(
    limit: int = None,
) -> List[Dict]:

    return PHRASES[
        :(
            limit
            or settings.MAX_PHRASES
        )
    ]


# ============================================================
# ROOT CANDIDATES
# ============================================================

def find_root_candidates(
    message: str,
) -> List[str]:

    return [
        token
        for token
        in _tokenize(message)
        if re.search(
            r"[\u0C00-\u0C7F]",
            token,
        )
    ]


# ============================================================
# LEARNING
# ============================================================

def add_vocab_entry(
    standard: str,
    melimi: str,
    note: str = "",
) -> bool:

    global VOCABULARY


    for entry in VOCABULARY:

        if (
            _normalize(
                entry.get(
                    "standard",
                    "",
                )
            )
            ==
            _normalize(
                standard
            )
            and
            _normalize(
                entry.get(
                    "melimi",
                    "",
                )
            )
            ==
            _normalize(
                melimi
            )
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

    if kind not in (
        "prefixes",
        "suffixes",
        "reduplication",
    ):

        raise ValueError(
            "Invalid grammar kind"
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

        if (
            entry.get(
                key
            )
            == element
        ):

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
