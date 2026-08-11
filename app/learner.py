import json
import os
import re
from typing import Any, Dict, List, Optional, Set


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


def normalize_word(
    word: str,
) -> str:

    return normalize_text(
        word
    ).lower()


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

            data = json.load(
                file
            )

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):

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

    word = normalize_word(
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

    entry = words[
        word
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
# VARIATION LEARNING
# ============================================================

def learn_variation(
    data: Dict[str, Any],
    surface_form: str,
    possible_base: str,
    document_id: str,
    sentence: str,
    relation: str = "observed_variation",
) -> None:

    surface_form = normalize_word(
        surface_form
    )

    possible_base = normalize_word(
        possible_base
    )

    if not surface_form:
        return

    if not possible_base:
        return

    if surface_form == possible_base:
        return

    variations = data[
        "variations"
    ]

    if surface_form not in variations:

        variations[
            surface_form
        ] = {}

    if possible_base not in variations[
        surface_form
    ]:

        variations[
            surface_form
        ][
            possible_base
        ] = {
            "count": 0,
            "relation": relation,
            "documents": {},
            "examples": [],
        }

    entry = variations[
        surface_form
    ][
        possible_base
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
# OBSERVED VARIATION CANDIDATES
# ============================================================

def possible_surface_bases(
    word: str,
) -> List[str]:

    """
    Generate conservative candidates for an observed
    grammatical surface form.

    These are NOT declared to be official Melimi
    grammatical rules.

    They are only candidate relationships that can
    later be strengthened by repeated corpus usage.
    """

    word = normalize_word(
        word
    )

    if not word:
        return []

    candidates: Set[str] = set()

    # --------------------------------------------------------
    # PLURAL / CASE FORMS
    # --------------------------------------------------------

    suffixes = [
        "లతో",
        "లలో",
        "లకు",
        "లను",
        "లని",
        "లపై",
        "లకై",
        "లకూ",
        "లవల్ల",
    ]

    for suffix in suffixes:

        if (
            word.endswith(suffix)
            and len(word)
            > len(suffix) + 1
        ):

            root = word[
                :-len(suffix)
            ]

            if root:

                candidates.add(
                    root
                )

    # --------------------------------------------------------
    # SIMPLE PLURAL
    # --------------------------------------------------------

    if (
        word.endswith("లు")
        and len(word) > 3
    ):

        candidates.add(
            word[:-2]
        )

    # --------------------------------------------------------
    # COMMON CASE FORMS
    # --------------------------------------------------------

    case_suffixes = [
        "లోని",
        "నుంచి",
        "నుండి",
        "యొక్క",
        "కోసం",
        "గురించి",
        "పైన",
        "వల్ల",
        "తోటి",
        "తో",
        "లో",
        "ను",
        "ని",
        "కు",
        "కి",
        "కూ",
        "పై",
        "గా",
    ]

    for suffix in case_suffixes:

        if (
            word.endswith(suffix)
            and len(word)
            > len(suffix) + 1
        ):

            root = word[
                :-len(suffix)
            ]

            if root:

                candidates.add(
                    root
                )

    # --------------------------------------------------------
    # COMMON VERBAL / NOMINAL SURFACE ENDINGS
    # --------------------------------------------------------
    #
    # These are deliberately treated as candidates only.
    #
    # They are NOT automatically accepted as Melimi rules.
    # --------------------------------------------------------

    possible_endings = [
        "ంగా",
        "ముగా",
        "మై",
        "మైన",
        "మైనా",
        "మును",
        "మున",
        "ము",
        "ం",
    ]

    for ending in possible_endings:

        if (
            word.endswith(ending)
            and len(word)
            > len(ending) + 1
        ):

            root = word[
                :-len(ending)
            ]

            if root:

                candidates.add(
                    root
                )

    return sorted(
        candidates,
        key=len,
        reverse=True,
    )


# ============================================================
# LEARN VARIATIONS FROM CORPUS
# ============================================================

def learn_surface_variations(
    data: Dict[str, Any],
    words: List[str],
    document_id: str,
    sentence: str,
) -> int:

    learned = 0

    unique_words = list(
        dict.fromkeys(
            normalize_word(
                word
            )
            for word in words
        )
    )

    known_words = set(
        data[
            "words"
        ].keys()
    )

    for surface_word in unique_words:

        if not surface_word:
            continue

        candidates = (
            possible_surface_bases(
                surface_word
            )
        )

        for candidate in candidates:

            # ------------------------------------------------
            # Only record candidate relationships when the
            # candidate has actually appeared elsewhere in
            # the corpus.
            #
            # This prevents arbitrary suffix stripping from
            # creating thousands of false "rules".
            # ------------------------------------------------

            if candidate not in known_words:

                continue

            learn_variation(
                data=data,
                surface_form=surface_word,
                possible_base=candidate,
                document_id=document_id,
                sentence=sentence,
            )

            learned += 1

    return learned


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

    variation_occurrences = 0

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
        # Store observed 2, 3 and 4 word sequences.
        #
        # They are corpus evidence, not automatically
        # declared grammatical rules.
        # ----------------------------------------------------

        for size in (
            2,
            3,
            4,
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
        # SENTENCE
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
    # VARIATIONS
    # --------------------------------------------------------
    #
    # Run AFTER learning the words so that a possible base
    # can be checked against the observed corpus vocabulary.
    # --------------------------------------------------------

    for sentence in sentences:

        words = tokenize(
            sentence
        )

        variation_occurrences += (
            learn_surface_variations(
                data=data,
                words=words,
                document_id=document_id,
                sentence=sentence,
            )
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

        "variation_occurrences":
            variation_occurrences,

        "total_words_known":
            len(
                data["words"]
            ),

        "total_phrases_known":
            len(
                data["phrases"]
            ),

        "total_variations_known":
            sum(
                len(value)
                for value
                in data[
                    "variations"
                ].values()
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
# SEARCH LEARNED VARIATIONS
# ============================================================

def search_learned_variations(
    message: str,
    limit: int = 12,
) -> Dict[str, Any]:

    data = load_database()

    query_words = set(
        tokenize(
            message
        )
    )

    results = []

    for surface_form, bases in data[
        "variations"
    ].items():

        if surface_form not in query_words:
            continue

        for base, info in bases.items():

            count = int(
                info.get(
                    "count",
                    0,
                )
            )

            score = (
                1200
                + count
                + len(base)
            )

            results.append(
                (
                    score,
                    surface_form,
                    base,
                    info,
                )
            )

    results.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    output = {}

    for (
        _,
        surface_form,
        base,
        info,
    ) in results[:limit]:

        if surface_form not in output:

            output[
                surface_form
            ] = []

        output[
            surface_form
        ].append(
            {
                "base": base,
                "count": info.get(
                    "count",
                    0,
                ),
                "relation": info.get(
                    "relation",
                    "observed_variation",
                ),
                "examples": info.get(
                    "examples",
                    [],
                ),
            }
        )

    return output


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

        word_count = len(
            tokenize(
                phrase
            )
        )

        score = (
            1000
            + count
            + (
                word_count
                * 100
            )
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
# SEARCH COMPLETE LEARNED CORPUS
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

        "variations":
            search_learned_variations(
                message,
                limit,
            ),
    }


# ============================================================
# BUILD CONTEXT FOR AI
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
    # OBSERVED WORDS
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
    # OBSERVED PHRASES
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

    # --------------------------------------------------------
    # OBSERVED VARIATIONS
    # --------------------------------------------------------

    variations = results[
        "variations"
    ]

    if variations:

        lines = [
            "OBSERVED MELIMI WORD VARIATIONS:"
        ]

        for surface, bases in (
            variations.items()
        ):

            for item in bases:

                base = item.get(
                    "base",
                    "",
                )

                count = item.get(
                    "count",
                    0,
                )

                relation = item.get(
                    "relation",
                    "observed_variation",
                )

                examples = item.get(
                    "examples",
                    [],
                )

                line = (
                    f"- {surface}"
                    f" → possible base: {base}"
                    f" | observed {count} times"
                    f" | relation: {relation}"
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
    # LIMIT CONTEXT SIZE
    # --------------------------------------------------------

    context = "\n\n".join(
        sections
    )

    if len(context) > max_chars:

        context = context[
            :max_chars
        ]

    return context


# ============================================================
# GET LEARNED EXAMPLES FOR A WORD
# ============================================================

def get_word_examples(
    word: str,
    limit: int = 5,
) -> List[str]:

    data = load_database()

    word = normalize_word(
        word
    )

    info = data[
        "words"
    ].get(
        word
    )

    if not info:

        return []

    return info.get(
        "examples",
        [],
    )[:limit]


# ============================================================
# GET PHRASE EXAMPLES
# ============================================================

def get_phrase_examples(
    phrase: str,
    limit: int = 5,
) -> List[str]:

    data = load_database()

    phrase = normalize_text(
        phrase
    )

    info = data[
        "phrases"
    ].get(
        phrase
    )

    if not info:

        return []

    return info.get(
        "examples",
        [],
    )[:limit]


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

        "variations":
            sum(
                len(value)
                for value
                in data[
                    "variations"
                ].values()
            ),
    }
