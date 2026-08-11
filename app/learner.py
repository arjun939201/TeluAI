import json
import os
import re
from typing import Any, Dict, List


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
)

LEARNED_FILE = os.path.join(
    DATA_DIR,
    "learned_corpus.json",
)


# ============================================================
# TELUGU TOKENIZATION
# ============================================================

TELUGU_WORD_RE = re.compile(
    r"[\u0C00-\u0C7F]+",
    re.UNICODE,
)


def normalize_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )


def tokenize(
    text: str,
) -> List[str]:

    return TELUGU_WORD_RE.findall(
        text or ""
    )


# ============================================================
# DATABASE
# ============================================================

def empty_database() -> Dict[str, Any]:

    return {
        "words": {},
        "phrases": {},
        "sentences": [],
        "documents": {},
        "variations": {},
    }


def load_database() -> Dict[str, Any]:

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    if not os.path.exists(
        LEARNED_FILE
    ):

        data = empty_database()

        save_database(
            data
        )

        return data

    try:

        with open(
            LEARNED_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except Exception:

        data = empty_database()

    defaults = empty_database()

    for key, default_value in (
        defaults.items()
    ):

        if key not in data:

            if isinstance(
                default_value,
                dict,
            ):

                data[key] = {}

            elif isinstance(
                default_value,
                list,
            ):

                data[key] = []

            else:

                data[key] = default_value

    return data


def save_database(
    data: Dict[str, Any],
) -> None:

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    temporary_file = (
        LEARNED_FILE
        + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        LEARNED_FILE,
    )


# ============================================================
# WORD LEARNING
# ============================================================

def learn_word(
    data: Dict[str, Any],
    word: str,
    document_id: str,
    sentence: str,
) -> None:

    word = normalize_text(
        word
    )

    if not word:
        return

    words = data[
        "words"
    ]

    if word not in words:

        words[word] = {
            "count": 0,
            "documents": {},
            "examples": [],
        }

    entry = words[word]

    entry[
        "count"
    ] += 1

    documents = entry[
        "documents"
    ]

    documents[
        document_id
    ] = (
        documents.get(
            document_id,
            0,
        )
        + 1
    )

    examples = entry[
        "examples"
    ]

    if (
        sentence
        and sentence not in examples
        and len(examples) < 5
    ):

        examples.append(
            sentence
        )


# ============================================================
# PHRASE LEARNING
# ============================================================

def learn_phrase(
    data: Dict[str, Any],
    phrase: str,
    document_id: str,
    sentence: str,
) -> None:

    phrase = normalize_text(
        phrase
    )

    if not phrase:
        return

    phrases = data[
        "phrases"
    ]

    if phrase not in phrases:

        phrases[phrase] = {
            "count": 0,
            "documents": {},
            "examples": [],
        }

    entry = phrases[
        phrase
    ]

    entry[
        "count"
    ] += 1

    documents = entry[
        "documents"
    ]

    documents[
        document_id
    ] = (
        documents.get(
            document_id,
            0,
        )
        + 1
    )

    examples = entry[
        "examples"
    ]

    if (
        sentence
        and sentence not in examples
        and len(examples) < 5
    ):

        examples.append(
            sentence
        )


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def split_sentences(
    text: str,
) -> List[str]:

    pieces = re.split(
        r"[.!?。！？\n]+",
        text,
    )

    sentences = []

    for piece in pieces:

        sentence = normalize_text(
            piece
        )

        if sentence:

            sentences.append(
                sentence
            )

    return sentences


# ============================================================
# LEARN COMPLETE TEXT
# ============================================================

def learn_text(
    text: str,
    document_id: str = "user_text",
) -> Dict[str, Any]:

    text = normalize_text(
        text
    )

    if not text:

        return {
            "learned": False,
            "reason": "empty text",
        }

    data = load_database()

    # --------------------------------------------------------
    # DOCUMENT
    # --------------------------------------------------------

    if document_id not in data[
        "documents"
    ]:

        data[
            "documents"
        ][document_id] = {
            "count": 0,
            "characters": 0,
        }

    data[
        "documents"
    ][document_id][
        "count"
    ] += 1

    data[
        "documents"
    ][document_id][
        "characters"
    ] += len(text)

    # --------------------------------------------------------
    # SENTENCES
    # --------------------------------------------------------

    sentences = split_sentences(
        text
    )

    unique_words = set()

    word_occurrences = 0

    phrase_occurrences = 0

    # --------------------------------------------------------
    # PROCESS SENTENCES
    # --------------------------------------------------------

    for sentence in sentences:

        words = tokenize(
            sentence
        )

        if not words:
            continue

        unique_words.update(
            words
        )

        word_occurrences += len(
            words
        )

        # ----------------------------------------------------
        # WORDS
        # ----------------------------------------------------

        for word in words:

            learn_word(
                data=data,
                word=word,
                document_id=document_id,
                sentence=sentence,
            )

        # ----------------------------------------------------
        # PHRASES
        # ----------------------------------------------------
        #
        # We record observed 2-word and 3-word sequences.
        #
        # We do NOT automatically declare them grammatical
        # rules.
        #
        # They are corpus evidence only.
        # ----------------------------------------------------

        for size in (
            2,
            3,
        ):

            if len(words) < size:
                continue

            for index in range(
                len(words) - size + 1
            ):

                phrase = " ".join(
                    words[
                        index:
                        index + size
                    ]
                )

                learn_phrase(
                    data=data,
                    phrase=phrase,
                    document_id=document_id,
                    sentence=sentence,
                )

                phrase_occurrences += 1

        # ----------------------------------------------------
        # SENTENCES
        # ----------------------------------------------------

        if sentence not in data[
            "sentences"
        ]:

            data[
                "sentences"
            ].append(
                sentence
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_database(
        data
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "learned": True,

        "document_id":
            document_id,

        "sentences_added":
            len(sentences),

        "word_occurrences":
            word_occurrences,

        "unique_words":
            len(unique_words),

        "phrase_occurrences":
            phrase_occurrences,

        "total_words_known":
            len(
                data["words"]
            ),

        "total_phrases_known":
            len(
                data["phrases"]
            ),

        "total_sentences":
            len(
                data["sentences"]
            ),

        "total_documents":
            len(
                data["documents"]
            ),
    }


# ============================================================
# SEARCH LEARNED WORDS
# ============================================================

def search_learned_words(
    message: str,
    limit: int = 8,
) -> Dict[str, Any]:

    data = load_database()

    query_words = set(
        tokenize(
            message
        )
    )

    scored = []

    for word, info in data[
        "words"
    ].items():

        if word not in query_words:
            continue

        count = int(
            info.get(
                "count",
                0,
            )
        )

        score = (
            1000
            + count
        )

        scored.append(
            (
                score,
                word,
                info,
            )
        )

    scored.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    results = {}

    for _, word, info in scored[
        :limit
    ]:

        results[word] = info

    return results


# ============================================================
# SEARCH LEARNED PHRASES
# ============================================================

def search_learned_phrases(
    message: str,
    limit: int = 8,
) -> Dict[str, Any]:

    data = load_database()

    normalized_message = (
        normalize_text(
            message
        )
    )

    scored = []

    for phrase, info in data[
        "phrases"
    ].items():

        if phrase not in normalized_message:
            continue

        count = int(
            info.get(
                "count",
                0,
            )
        )

        score = (
            1000
            + count
            + len(phrase)
        )

        scored.append(
            (
                score,
                phrase,
                info,
            )
        )

    scored.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    results = {}

    for _, phrase, info in scored[
        :limit
    ]:

        results[phrase] = info

    return results


# ============================================================
# SEARCH LEARNED CORPUS
# ============================================================

def search_learned(
    message: str,
    limit: int = 8,
) -> Dict[str, Any]:

    return {
        "words":
            search_learned_words(
                message,
                limit,
            ),

        "phrases":
            search_learned_phrases(
                message,
                limit,
            ),
    }


# ============================================================
# BUILD GROQ CONTEXT
# ============================================================

def build_learned_context(
    message: str,
    limit: int = 8,
    max_chars: int = 5000,
) -> str:

    results = search_learned(
        message,
        limit,
    )

    sections = []

    # --------------------------------------------------------
    # WORDS
    # --------------------------------------------------------

    words = results[
        "words"
    ]

    if words:

        lines = [
            "OBSERVED MELIMI WORD USAGE:"
        ]

        for word, info in words.items():

            count = info.get(
                "count",
                0,
            )

            examples = info.get(
                "examples",
                [],
            )

            line = (
                f"- {word}"
                f" | observed {count} times"
            )

            if examples:

                line += (
                    f" | example: "
                    f"{examples[0]}"
                )

            lines.append(
                line
            )

        sections.append(
            "\n".join(lines)
        )

    # --------------------------------------------------------
    # PHRASES
    # --------------------------------------------------------

    phrases = results[
        "phrases"
    ]

    if phrases:

        lines = [
            "OBSERVED MELIMI PHRASES:"
        ]

        for phrase, info in phrases.items():

            count = info.get(
                "count",
                0,
            )

            examples = info.get(
                "examples",
                [],
            )

            line = (
                f"- {phrase}"
                f" | observed {count} times"
            )

            if examples:

                line += (
                    f" | example: "
                    f"{examples[0]}"
                )

            lines.append(
                line
            )

        sections.append(
            "\n".join(lines)
        )

    context = "\n\n".join(
        sections
    )

    if len(context) > max_chars:

        context = context[
            :max_chars
        ]

    return context


# ============================================================
# LEARNING STATISTICS
# ============================================================

def get_learning_stats() -> Dict[str, int]:

    data = load_database()

    return {
        "words":
            len(
                data["words"]
            ),

        "phrases":
            len(
                data["phrases"]
            ),

        "sentences":
            len(
                data["sentences"]
            ),

        "documents":
            len(
                data["documents"]
            ),
    }
