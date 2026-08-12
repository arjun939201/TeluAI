import json
import os
import re
from typing import Any, Dict, List


# ============================================================
# TELUAI MELIMI KNOWLEDGE RETRIEVER
# ============================================================
#
# IMPORTANT:
#
# This module NEVER generates sentences.
# This module NEVER rewrites the AI response.
# This module NEVER replaces words in the AI response.
#
# It only finds relevant Melimi knowledge and gives that
# knowledge to the language model.
#
# vocabulary.json remains authoritative.
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
# TEXT HELPERS
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


def split_forms(
    value: Any,
) -> List[str]:

    if value is None:

        return []


    if isinstance(
        value,
        list,
    ):

        values = value

    else:

        values = re.split(
            r"\s*(?:,|/|;|\|)\s*",
            str(value),
        )


    return [
        normalize(item)
        for item in values
        if normalize(item)
    ]


# ============================================================
# LOAD VOCABULARY
# ============================================================

def load_vocabulary() -> List[Dict[str, Any]]:

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
            "entries",
            "data",
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


VOCABULARY = load_vocabulary()


# ============================================================
# COMMON CONVERSATIONAL HINTS
# ============================================================
#
# These are ONLY search hints.
#
# They are NOT response templates.
# ============================================================

CONVERSATION_HINTS = {

    "hi": {
        "greeting",
        "hello",
        "greet",
        "నమస్కారం",
    },

    "hello": {
        "greeting",
        "hello",
        "greet",
        "నమస్కారం",
    },

    "hey": {
        "greeting",
        "hello",
        "greet",
    },

    "thanks": {
        "thanks",
        "thank",
        "gratitude",
        "నెనరు",
    },

    "thank": {
        "thanks",
        "thank",
        "gratitude",
        "నెనరు",
    },

    "thankyou": {
        "thanks",
        "thank",
        "gratitude",
        "నెనరు",
    },

    "help": {
        "help",
        "assistance",
        "support",
        "బాసట",
    },

    "ok": {
        "okay",
        "agreement",
    },

    "okay": {
        "okay",
        "agreement",
    },

    "yes": {
        "yes",
        "agreement",
    },

    "no": {
        "no",
        "negation",
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
# SEARCHABLE TEXT
# ============================================================

def entry_search_text(
    entry: Dict[str, Any],
) -> str:

    values = []


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
        "tags",
        "category",
        "related",
        "synonyms",
    ):

        value = entry.get(
            key,
            "",
        )


        if isinstance(
            value,
            list,
        ):

            values.extend(
                str(item)
                for item in value
            )

        elif isinstance(
            value,
            dict,
        ):

            values.extend(
                str(item)
                for item in value.values()
            )

        else:

            values.append(
                str(value)
            )


    return normalize(
        " ".join(values)
    )


# ============================================================
# WORD MATCH
# ============================================================

def contains_form(
    text: str,
    form: str,
) -> bool:

    text = normalize(
        text
    )

    form = normalize(
        form
    )


    if not text or not form:

        return False


    if " " in form:

        return form in text


    words = {
        normalize(word)
        for word in WORD_RE.findall(
            text
        )
    }


    return form in words


# ============================================================
# RETRIEVE CONVERSATIONAL KNOWLEDGE
# ============================================================

def retrieve_conversation_context(
    message: str,
    limit: int = 6,
    max_chars: int = 1400,
) -> str:
    """
    Retrieve relevant Melimi knowledge.

    IMPORTANT:
    The returned material is KNOWLEDGE, not a response template.

    Groq must independently construct the final sentence.
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
            CONVERSATION_HINTS.get(
                word,
                set(),
            )
        )


    scored = []


    for index, entry in enumerate(
        VOCABULARY
    ):

        standard_forms = split_forms(
            entry.get(
                "standard",
                "",
            )
        )


        melimi_forms = split_forms(
            entry.get(
                "melimi",
                "",
            )
        )


        search_text = entry_search_text(
            entry
        )


        score = 0


        # ----------------------------------------------------
        # Direct user-word match
        # ----------------------------------------------------

        for form in (
            standard_forms
            + melimi_forms
        ):

            if contains_form(
                query,
                form,
            ):

                score += 500


        # ----------------------------------------------------
        # Conversational intent
        # ----------------------------------------------------

        for hint in hints:

            if hint in search_text:

                score += 100


        # ----------------------------------------------------
        # Query-word overlap
        # ----------------------------------------------------

        for word in query_words:

            if word in search_text:

                score += 25


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


    lines = [
        "RELEVANT MELIMI KNOWLEDGE:"
    ]


    seen = set()


    for (
        _score,
        _index,
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


        note = str(
            entry.get(
                "note",
                "",
            )
        ).strip()


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


        identity = (
            standard,
            melimi,
            note,
        )


        if identity in seen:

            continue


        seen.add(
            identity
        )


        if not (
            standard
            or melimi
        ):

            continue


        line = (
            f"- standard: {standard}"
            f" | melimi: {melimi}"
        )


        if meaning:

            line += (
                f" | meaning: {meaning}"
            )


        if note:

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
        ):

            break


        if (
            len(lines) - 1
            >= limit
        ):

            break


    if len(lines) == 1:

        return ""


    return "\n".join(
        lines
    )[
        :max_chars
    ]
