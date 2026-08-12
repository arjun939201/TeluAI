import json
import os
import re
from typing import Any, Dict, List, Tuple


# ============================================================
# TELUAI MELIMI ENGINE
# ============================================================
#
# This module provides:
#
# 1. Relevant Melimi vocabulary for conversational inputs
# 2. Standard → Melimi output validation
#
# vocabulary.json remains the authority.
#
# No Melimi words are invented here.
# ============================================================


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


VOCABULARY_FILE = os.path.join(
    BASE_DIR,
    "data",
    "vocabulary.json",
)


# ============================================================
# TOKENIZATION
# ============================================================

WORD_RE = re.compile(
    r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*",
    re.UNICODE,
)


def normalize(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
        .strip()
        .lower(),
    )


# ============================================================
# SPLIT STANDARD / MELIMI ALTERNATIVES
# ============================================================

def split_forms(
    value: Any,
) -> List[str]:

    if value is None:

        return []


    if isinstance(
        value,
        list,
    ):

        raw = value

    else:

        raw = re.split(
            r"\s*(?:,|/|;|\||\s+లేదా\s+)\s*",
            str(value),
            flags=re.IGNORECASE,
        )


    return [
        normalize(item)
        for item in raw
        if normalize(item)
    ]


# ============================================================
# LOAD VOCABULARY
# ============================================================

def _load_vocabulary() -> List[Dict[str, Any]]:

    if not os.path.exists(
        VOCABULARY_FILE
    ):

        return []


    try:

        with open(
            VOCABULARY_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

    except Exception:

        return []


    if isinstance(
        data,
        list,
    ):

        return [
            item
            for item in data
            if isinstance(
                item,
                dict,
            )
        ]


    if isinstance(
        data,
        dict,
    ):

        for key in (
            "vocabulary",
            "words",
        ):

            value = data.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                return [
                    item
                    for item in value
                    if isinstance(
                        item,
                        dict,
                    )
                ]


    return []


VOCABULARY = _load_vocabulary()


# ============================================================
# COMMON CONVERSATIONAL INTENTS
# ============================================================
#
# These are ONLY retrieval hints.
#
# They are not Melimi vocabulary.
#
# The actual Melimi answer must come from vocabulary.json
# and the Melimi system rules.
# ============================================================

INTENT_HINTS = {

    "hi": {
        "greeting",
        "hello",
        "greet",
    },

    "hello": {
        "greeting",
        "hello",
        "greet",
    },

    "hey": {
        "greeting",
        "hello",
        "greet",
    },

    "hiya": {
        "greeting",
        "hello",
        "greet",
    },

    "thanks": {
        "thanks",
        "thank",
        "gratitude",
    },

    "thank": {
        "thanks",
        "thank",
        "gratitude",
    },

    "thankyou": {
        "thanks",
        "thank",
        "gratitude",
    },

    "welcome": {
        "welcome",
        "greeting",
    },

    "help": {
        "help",
        "assistance",
        "support",
    },

    "yes": {
        "yes",
        "agreement",
    },

    "no": {
        "no",
        "negation",
    },

    "okay": {
        "okay",
        "agreement",
    },

    "ok": {
        "okay",
        "agreement",
    },

    "good": {
        "good",
        "well",
    },

    "morning": {
        "morning",
    },

    "evening": {
        "evening",
    },

    "night": {
        "night",
    },
}


# ============================================================
# SEARCHABLE ENTRY TEXT
# ============================================================

def _search_text(
    entry: Dict[str, Any],
) -> str:

    fields = []


    for key in (
        "standard",
        "melimi",
        "note",
        "meaning",
        "definition",
        "english",
        "gloss",
        "description",
        "example",
        "examples",
        "related",
        "synonyms",
        "tags",
    ):

        value = entry.get(
            key,
            "",
        )


        if isinstance(
            value,
            list,
        ):

            fields.extend(
                str(item)
                for item in value
            )

        elif isinstance(
            value,
            dict,
        ):

            fields.extend(
                str(item)
                for item in value.values()
            )

        else:

            fields.append(
                str(value)
            )


    return normalize(
        " ".join(fields)
    )


# ============================================================
# CONTAINS
# ============================================================

def _contains(
    text: str,
    phrase: str,
) -> bool:

    text = normalize(
        text
    )

    phrase = normalize(
        phrase
    )


    if not text or not phrase:

        return False


    if " " in phrase:

        return phrase in text


    words = {
        normalize(word)
        for word in WORD_RE.findall(
            text
        )
    }


    return phrase in words


# ============================================================
# CONVERSATION CONTEXT
# ============================================================

def retrieve_conversation_context(
    message: str,
    limit: int = 6,
    max_chars: int = 1400,
) -> str:
    """
    Retrieve a small amount of relevant vocabulary for
    common conversational messages.

    Example:

        hi
        ↓
        greeting
        ↓
        vocabulary.json
        ↓
        relevant Melimi greeting
    """

    query = normalize(
        message
    )


    if not query:

        return ""


    query_words = {
        normalize(word)
        for word in WORD_RE.findall(
            query
        )
    }


    hints = set()


    for word in query_words:

        hints.update(
            INTENT_HINTS.get(
                word,
                set(),
            )
        )


    scored: List[
        Tuple[
            int,
            int,
            Dict[str, Any],
        ]
    ] = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standard = split_forms(
            entry.get(
                "standard",
                "",
            )
        )


        melimi = split_forms(
            entry.get(
                "melimi",
                "",
            )
        )


        search = _search_text(
            entry
        )


        score = 0


        # ----------------------------------------------------
        # Exact vocabulary match
        # ----------------------------------------------------

        for form in (
            standard
            + melimi
        ):

            if _contains(
                query,
                form,
            ):

                score += 500


        # ----------------------------------------------------
        # Query words in entry
        # ----------------------------------------------------

        for word in query_words:

            if _contains(
                search,
                word,
            ):

                score += 30


        # ----------------------------------------------------
        # Intent hints
        # ----------------------------------------------------

        for hint in hints:

            if hint in search:

                score += 100


        if score:

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


    lines = [
        "RELEVANT MELIMI CONVERSATION VOCABULARY:"
    ]


    seen = set()


    for (
        _,
        _,
        entry,
    ) in scored:

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


        marker = (
            standard,
            melimi,
        )


        if marker in seen:

            continue


        seen.add(
            marker
        )


        line = (
            f"- {standard}"
            f" → {melimi}"
        )


        meaning = str(
            entry.get(
                "meaning",
                entry.get(
                    "definition",
                    entry.get(
                        "english",
                        "",
                    ),
                ),
            )
        ).strip()


        note = str(
            entry.get(
                "note",
                "",
            )
        ).strip()


        if meaning:

            line += (
                f" | meaning: {meaning}"
            )

        elif note:

            line += (
                f" | note: {note}"
            )


        lines.append(
            line
        )


        if (
            len(
                "\n".join(lines)
            ) >= max_chars
            or
            len(lines) - 1 >= limit
        ):

            break


    if len(lines) == 1:

        return ""


    return "\n".join(
        lines
    )[
        :max_chars
    ]


# ============================================================
# WHOLE-WORD / WHOLE-PHRASE PATTERN
# ============================================================

def _replacement_pattern(
    form: str,
) -> re.Pattern:

    escaped = re.escape(
        form.strip()
    )


    return re.compile(
        rf"(?<![\u0C00-\u0C7FA-Za-z])"
        rf"{escaped}"
        rf"(?![\u0C00-\u0C7FA-Za-z])",
        re.IGNORECASE,
    )


# ============================================================
# MELIMI OUTPUT VALIDATOR
# ============================================================

def validate_melimi_response(
    response: str,
    max_replacements: int = 20,
) -> Tuple[
    str,
    List[Dict[str, str]],
]:
    """
    Validate a generated Melimi response against the
    authoritative vocabulary.

    Example:

        సహాయం
            ↓
        vocabulary.json
            ↓
        బాసట

    No hardcoded word mappings are used.
    """

    if not response:

        return (
            response,
            [],
        )


    candidates = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standards = split_forms(
            entry.get(
                "standard",
                "",
            )
        )


        melimis = split_forms(
            entry.get(
                "melimi",
                "",
            )
        )


        if not standards:

            continue


        if not melimis:

            continue


        # First Melimi form is the primary form.

        melimi = melimis[0]


        for standard in standards:

            if not standard:

                continue


            if standard == melimi:

                continue


            candidates.append(
                (
                    len(standard),
                    index,
                    standard,
                    melimi,
                )
            )


    # Longest first.
    #
    # This prevents:
    #
    # phrase containing word
    #
    # from being destroyed by a shorter match.

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )


    result = response


    changes: List[
        Dict[str, str]
    ] = []


    for (
        _,
        _,
        standard,
        melimi,
    ) in candidates:

        if len(changes) >= max_replacements:

            break


        pattern = _replacement_pattern(
            standard
        )


        if not pattern.search(
            result
        ):

            continue


        # If the Melimi equivalent is already present,
        # do not unnecessarily modify the answer.

        melimi_pattern = (
            _replacement_pattern(
                melimi
            )
        )


        if melimi_pattern.search(
            result
        ):

            continue


        new_result, count = (
            pattern.subn(
                melimi,
                result,
            )
        )


        if count:

            changes.append(
                {
                    "standard": standard,
                    "melimi": melimi,
                }
            )


            result = new_result


    return (
        result,
        changes,
    )
