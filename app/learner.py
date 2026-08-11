import json
import os
import re
from collections import Counter
from typing import Dict, List


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
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
# TELUGU
# ============================================================

TELUGU_WORD_RE = re.compile(
    r"[\u0C00-\u0C7F]+",
    re.UNICODE,
)


def tokenize(text: str) -> List[str]:

    return TELUGU_WORD_RE.findall(
        text or ""
    )


def normalize(text: str) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )


# ============================================================
# DATABASE
# ============================================================

DEFAULT_DATA = {
    "words": {},
    "phrases": {},
    "variations": {},
    "sentences": [],
    "documents": [],
}


def load_learned() -> Dict:

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    if not os.path.exists(
        LEARNED_FILE
    ):

        save_learned(
            DEFAULT_DATA.copy()
        )

        return {
            "words": {},
            "phrases": {},
            "variations": {},
            "sentences": [],
            "documents": [],
        }


    try:

        with open(
            LEARNED_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)


        for key, default in DEFAULT_DATA.items():

            if key not in data:

                data[key] = (
                    default.copy()
                    if isinstance(
                        default,
                        dict,
                    )
                    else list(default)
                )


        return data


    except Exception:

        return {
            "words": {},
            "phrases": {},
            "variations": {},
            "sentences": [],
            "documents": [],
        }


def save_learned(
    data: Dict,
) -> None:

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    temporary = (
        LEARNED_FILE
        + ".tmp"
    )


    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


    os.replace(
        temporary,
        LEARNED_FILE,
    )


# ============================================================
# WORD LEARNING
# ============================================================

def learn_word(
    word: str,
    document_id: str,
) -> None:

    word = normalize(
        word
    )

    if not word:
        return


    data = load_learned()

    words = data["words"]


    if word not in words:

        words[word] = {
            "count": 0,
            "documents": [],
            "examples": [],
        }


    words[word]["count"] += 1


    if (
        document_id
        not in words[word]["documents"]
    ):

        words[word]["documents"].append(
            document_id
        )


# ============================================================
# SENTENCE LEARNING
# ============================================================

def learn_sentences(
    text: str,
    document_id: str,
) -> int:

    data = load_learned()

    sentences = re.split(
        r"[.!?。\n]+",
        text,
    )


    count = 0


    for sentence in sentences:

        sentence = normalize(
            sentence
        )

        if len(sentence) < 3:
            continue


        if sentence not in data[
            "sentences"
        ]:

            data[
                "sentences"
            ].append(
                sentence
            )

            count += 1


    return count


# ============================================================
# PHRASE LEARNING
# ============================================================

def learn_phrases(
    text: str,
    document_id: str,
) -> None:

    data = load_learned()

    words = tokenize(
        text
    )


    # Learn 2-word and 3-word
    # sequences from actual corpus usage.

    for size in (
        2,
        3,
    ):

        for i in range(
            len(words) - size + 1
        ):

            phrase = " ".join(
                words[
                    i:i + size
                ]
            )


            if phrase not in data[
                "phrases"
            ]:

                data[
                    "phrases"
                ][phrase] = {
                    "count": 0,
                    "documents": [],
                    "examples": [],
                }


            item = data[
                "phrases"
            ][phrase]


            item["count"] += 1


            if (
                document_id
                not in item[
                    "documents"
                ]
            ):

                item[
                    "documents"
                ].append(
                    document_id
                )


            if (
                text not in item[
                    "examples"
                ]
                and len(
                    item["examples"]
                ) < 5
            ):

                item[
                    "examples"
                ].append(
                    text
                )


# ============================================================
# VARIATION LEARNING
# ============================================================

COMMON_VARIATION_ENDINGS = [
    "లను",
    "లతో",
    "లకు",
    "లలో",
    "లపై",
    "లని",
    "లు",
    "ాన్ని",
    "ాన్ని",
    "ానికి",
    "ానికి",
    "ంలో",
    "లో",
    "తో",
    "ను",
    "ని",
    "కు",
    "కి",
    "పై",
]


def possible_bases(
    word: str,
) -> List[str]:

    results = []


    for ending in sorted(
        COMMON_VARIATION_ENDINGS,
        key=len,
        reverse=True,
    ):

        if (
            word.endswith(
                ending
            )
            and len(word)
            > len(ending) + 1
        ):

            base = word[
                : -len(ending)
            ]

            if base:

                results.append(
                    base
                )


    results.append(
        word
    )


    return list(
        dict.fromkeys(
            results
        )
    )


def learn_variations(
    text: str,
    document_id: str,
) -> None:

    data = load_learned()

    words = tokenize(
        text
    )


    for word in words:

        bases = possible_bases(
            word
        )


        if len(bases) <= 1:
            continue


        base = bases[0]


        if base == word:
            continue


        if base not in data[
            "variations"
        ]:

            data[
                "variations"
            ][base] = {
                "forms": {},
                "documents": [],
            }


        item = data[
            "variations"
        ][base]


        item[
            "forms"
        ][word] = (
            item[
                "forms"
            ].get(
                word,
                0,
            )
            + 1
        )


        if (
            document_id
            not in item[
                "documents"
            ]
        ):

            item[
                "documents"
            ].append(
                document_id
            )


# ============================================================
# DOCUMENT LEARNING
# ============================================================

def learn_text(
    text: str,
    document_id: str = "unknown",
) -> Dict:

    text = normalize(
        text
    )


    if not text:

        return {
            "learned": False,
            "words": 0,
            "phrases": 0,
            "variations": 0,
        }


    data = load_learned()


    # --------------------------------------------------------
    # DOCUMENT
    # --------------------------------------------------------

    if document_id not in data[
        "documents"
    ]:

        data[
            "documents"
        ].append(
            document_id
        )


    # --------------------------------------------------------
    # WORDS
    # --------------------------------------------------------

    words = tokenize(
        text
    )


    for word in words:

        learn_word(
            word,
            document_id,
        )


    # --------------------------------------------------------
    # PHRASES
    # --------------------------------------------------------

    learn_phrases(
        text,
        document_id,
    )


    # --------------------------------------------------------
    # VARIATIONS
    # --------------------------------------------------------

    before = len(
        data[
            "variations"
        ]
    )


    learn_variations(
        text,
        document_id,
    )


    # --------------------------------------------------------
    # SENTENCES
    # --------------------------------------------------------

    learn_sentences(
        text,
        document_id,
    )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    data = load_learned()

    save_learned(
        data
    )


    return {
        "learned": True,
        "document": document_id,
        "words": len(words),
        "unique_words": len(
            set(words)
        ),
        "phrases": len(
            data["phrases"]
        ),
        "variations": (
            len(
                data[
                    "variations"
                ]
            )
        ),
        "sentences": len(
            data[
                "sentences"
            ]
        ),
    }


# ============================================================
# SEARCH LEARNED CORPUS
# ============================================================

def search_learned(
    message: str,
    limit: int = 10,
) -> Dict:

    data = load_learned()

    message_words = set(
        tokenize(
            message
        )
    )


    matched_words = {}

    for word, info in data[
        "words"
    ].items():

        if word in message_words:

            matched_words[
                word
            ] = info


    matched_phrases = {}

    normalized_message = normalize(
        message
    )


    for phrase, info in data[
        "phrases"
    ].items():

        if phrase in normalized_message:

            matched_phrases[
                phrase
            ] = info


    matched_variations = {}


    for base, info in data[
        "variations"
    ].items():

        forms = info.get(
            "forms",
            {},
        )


        for form in forms:

            if form in message:

                matched_variations[
                    base
                ] = info

                break


    return {
        "words": dict(
            list(
                matched_words.items()
            )[:limit]
        ),

        "phrases": dict(
            list(
                matched_phrases.items()
            )[:limit]
        ),

        "variations": dict(
            list(
                matched_variations.items()
            )[:limit]
        ),
    }


# ============================================================
# PROMPT CONTEXT
# ============================================================

def build_learned_context(
    message: str,
    limit: int = 10,
) -> str:

    result = search_learned(
        message,
        limit,
    )


    lines = []


    for word, info in result[
        "words"
    ].items():

        lines.append(
            f"- learned word: {word} "
            f"(seen {info.get('count', 0)} times)"
        )


    for phrase, info in result[
        "phrases"
    ].items():

        lines.append(
            f"- learned phrase: {phrase} "
            f"(seen {info.get('count', 0)} times)"
        )


    for base, info in result[
        "variations"
    ].items():

        forms = ", ".join(
            info.get(
                "forms",
                {},
            ).keys()
        )


        lines.append(
            f"- learned variation: "
            f"{base} → {forms}"
        )


    if not lines:

        return ""


    return "\n".join(
        lines
    )
