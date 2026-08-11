import json
import os
import re
from collections import Counter
from typing import Any, Dict, List


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(BASE_DIR, "data")

LEARNED_FILE = os.path.join(
    DATA_DIR,
    "learned_corpus.json",
)


TELUGU_WORD_RE = re.compile(
    r"[\u0C00-\u0C7F]+",
    re.UNICODE,
)


def normalize_text(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )


def tokenize(text: str) -> List[str]:
    return TELUGU_WORD_RE.findall(
        text or ""
    )


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
        save_database(data)
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

    for key, value in defaults.items():

        if key not in data:

            data[key] = value

    return data


def save_database(
    data: Dict[str, Any]
) -> None:

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    temp_file = LEARNED_FILE + ".tmp"

    with open(
        temp_file,
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
        temp_file,
        LEARNED_FILE,
    )


def learn_word(
    data: Dict[str, Any],
    word: str,
    document_id: str,
    sentence: str,
) -> None:

    if not word:
        return

    words = data["words"]

    if word not in words:

        words[word] = {
            "count": 0,
            "documents": {},
            "examples": [],
        }

    entry = words[word]

    entry["count"] += 1

    documents = entry["documents"]

    documents[document_id] = (
        documents.get(
            document_id,
            0,
        )
        + 1
    )

    if (
        sentence
        and sentence not in entry["examples"]
        and len(entry["examples"]) < 5
    ):

        entry["examples"].append(
            sentence
        )


def learn_phrase(
    data: Dict[str, Any],
    phrase: str,
    document_id: str,
    sentence: str,
) -> None:

    if not phrase:
        return

    phrases = data["phrases"]

    if phrase not in phrases:

        phrases[phrase] = {
            "count": 0,
            "documents": {},
            "examples": [],
        }

    entry = phrases[phrase]

    entry["count"] += 1

    documents = entry["documents"]

    documents[document_id] = (
        documents.get(
            document_id,
            0,
        )
        + 1
    )

    if (
        sentence
        and sentence not in entry["examples"]
        and len(entry["examples"]) < 5
    ):

        entry["examples"].append(
            sentence
        )


def split_sentences(
    text: str,
) -> List[str]:

    pieces = re.split(
        r"[.!?。！？\n]+",
        text,
    )

    return [
        normalize_text(piece)
        for piece in pieces
        if normalize_text(piece)
    ]


def learn_text(
    text: str,
    document_id: str = "user_text",
) -> Dict[str, Any]:

    text = normalize_text(text)

    if not text:

        return {
            "learned": False,
            "reason": "empty text",
        }

    data = load_database()

    data["documents"].setdefault(
        document_id,
        {
            "count": 0,
            "characters": 0,
        },
    )

    data["documents"][document_id][
        "count"
    ] += 1

    data["documents"][document_id][
        "characters"
    ] += len(text)

    sentences = split_sentences(
        text
    )

    unique_words = set()

    phrase_count = 0

    for sentence in sentences:

        words = tokenize(
            sentence
        )

        unique_words.update(
            words
        )

        for word in words:

            learn_word(
                data,
                word,
                document_id,
                sentence,
            )

        # Learn actual corpus phrases.
        #
        # 2-word and 3-word sequences.
        #
        # We don't claim these are grammatical
        # units. They are simply observed usage.

        for size in (2, 3):

            if len(words) < size:
                continue

            for index in range(
                len(words) - size + 1
            ):

                phrase = " ".join(
                    words[
                        index:index + size
                    ]
                )

                learn_phrase(
                    data,
                    phrase,
                    document_id,
                    sentence,
                )

                phrase_count += 1

        if sentence not in data[
            "sentences"
        ]:

            data[
                "sentences"
            ].append(sentence)

    save_database(
        data
    )

    return {
        "learned": True,
        "document_id": document_id,
        "sentences_added": len(
            sentences
        ),
        "word_occurrences": sum(
            len(tokenize(sentence))
            for sentence in sentences
        ),
        "unique_words": len(
            unique_words
        ),
        "phrases_observed": phrase_count,
        "total_words_known": len(
            data["words"]
        ),
        "total_phrases_known": len(
            data["phrases"]
        ),
    }


def _score_word_match(
    query_words: set,
    word: str,
    info: Dict[str, Any],
) -> float:

    if word in query_words:
        return 1000 + info.get(
            "count",
            0,
        )

    return 0


def search_learned(
    message: str,
    limit: int = 8,
) -> Dict[str, Any]:

    data = load_database()

    query_words = set(
        tokenize(message)
    )

    scored_words = []

    for word, info in data[
        "words"
    ].items():

        score = _score_word_match(
            query_words,
            word,
            info,
        )

        if score > 0:

            scored_words.append(
                (
                    score,
                    word,
                    info,
                )
            )

    scored_words.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    matched_words = {}

    for _, word, info in scored_words[
        :limit
    ]:

        matched_words[word] = info

    normalized_message = normalize_text(
        message
    )

    scored_phrases = []

    for phrase, info in data[
        "phrases"
    ].items():

        if phrase in normalized_message:

            score = (
                1000
                + info.get(
                    "count",
                    0,
                )
                + len(phrase)
            )

            scored_phrases.append(
                (
                    score,
                    phrase,
                    info,
                )
            )

    scored_phrases.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    matched_phrases = {}

    for _, phrase, info in scored_phrases[
        :limit
    ]:

        matched_phrases[
            phrase
        ] = info

    return {
        "words": matched_words,
        "phrases": matched_phrases,
    }


def build_learned_context(
    message: str,
    limit: int = 8,
    max_chars: int = 5000,
) -> str:

    result = search_learned(
        message,
        limit=limit,
    )

    parts = []

    words = result["words"]

    if words:

        parts.append(
            "OBSERVED MELIMI WORD USAGE:"
        )

        for word, info in words.items():

            examples = info.get(
                "examples",
                [],
            )

            line = (
                f"{word} "
                f"(observed {info.get('count', 0)} times)"
            )

            if examples:

                line += (
                    f" | example: {examples[0]}"
                )

            parts.append(line)

    phrases = result["phrases"]

    if phrases:

        parts.append(
            "\nOBSERVED MELIMI PHRASES:"
        )

        for phrase, info in phrases.items():

            examples = info.get(
                "examples",
                [],
            )

            line = (
                f"{phrase} "
                f"(observed {info.get('count', 0)} times)"
            )

            if examples:

                line += (
                    f" | example: {examples[0]}"
                )

            parts.append(line)

    context = "\n".join(
        parts
    )

    if len(context) > max_chars:

        context = context[
            :max_chars
        ]

    return context


def get_learning_stats() -> Dict[str, int]:

    data = load_database()

    return {
        "words": len(
            data["words"]
        ),
        "phrases": len(
            data["phrases"]
        ),
        "sentences": len(
            data["sentences"]
        ),
        "documents": len(
            data["documents"]
        ),
    }
