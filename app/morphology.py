import re
from typing import Dict, List, Optional


# ============================================================
# TELUGU MORPHOLOGY
# ============================================================

TELUGU_RE = re.compile(
    r"[\u0C00-\u0C7F]+",
    re.UNICODE,
)


# Common Telugu grammatical endings.
#
# These are used primarily for UNDERSTANDING a surface form.
# They are not treated as authoritative Melimi word-forming rules.
# Authoritative Melimi formations continue to come from grammar.json.
#
# Long endings must appear before short endings.
CASE_SUFFIXES = [
    "లతో",
    "లలో",
    "లకు",
    "లను",
    "లని",
    "లతో",
    "లకూ",
    "లపై",
    "లకై",
    "లవల్ల",

    "నుంచి",
    "నుండి",
    "యొక్క",

    "తోటి",
    "తో",
    "లో",
    "లు",
    "ను",
    "ని",
    "కు",
    "కి",
    "కూ",
    "గాను",
    "గా",
    "పై",
    "పైన",
    "లోని",
    "కోసం",
    "వల్ల",
    "మధ్య",
    "గురించి",
]


# Common nominal plural marker.
PLURAL_SUFFIXES = [
    "లు",
]


# Common singular case endings.
SINGULAR_CASE_SUFFIXES = [
    "లోని",
    "నుంచి",
    "నుండి",
    "యొక్క",
    "కోసం",
    "గురించి",
    "పైన",
    "వల్ల",
    "తోటి",
    "గా",
    "పై",
    "లో",
    "తో",
    "ను",
    "ని",
    "కు",
    "కి",
    "కూ",
]


def is_telugu_word(
    word: str,
) -> bool:

    return bool(
        TELUGU_RE.fullmatch(
            word or ""
        )
    )


def normalize_word(
    word: str,
) -> str:

    return (
        str(word or "")
        .strip()
        .lower()
    )


def _remove_one_suffix(
    word: str,
    suffixes: List[str],
) -> Optional[str]:

    word = normalize_word(
        word
    )

    for suffix in sorted(
        suffixes,
        key=len,
        reverse=True,
    ):

        if (
            word.endswith(suffix)
            and len(word)
            > len(suffix) + 1
        ):

            root = word[
                : -len(suffix)
            ]

            if root:

                return root


    return None


def analyze_surface_form(
    word: str,
) -> Dict:

    """
    Analyze a Telugu surface form.

    Example:

        ఎడాటాలు

    may produce:

        surface = ఎడాటాలు
        base_candidate = ఎడాట
        number = plural

    This is intentionally conservative.

    It does NOT claim that every possible form is a valid Melimi
    formation. It only helps TeluAI connect a grammatical surface
    form with a dictionary base.
    """

    surface = normalize_word(
        word
    )

    result = {
        "surface": surface,
        "base_candidates": [],
        "number": "singular",
        "case": None,
    }

    if not surface:
        return result


    # --------------------------------------------------------
    # PLURAL + CASE
    # --------------------------------------------------------

    plural_case_map = {
        "లతో": "instrumental/comitative",
        "లలో": "locative",
        "లకు": "dative",
        "లను": "accusative",
        "లని": "accusative",
        "లపై": "on",
        "లకై": "for",
    }


    for suffix, case_name in (
        plural_case_map.items()
    ):

        if (
            surface.endswith(suffix)
            and len(surface)
            > len(suffix) + 1
        ):

            root = surface[
                : -len(suffix)
            ]

            result[
                "base_candidates"
            ].append(root)

            result["number"] = "plural"
            result["case"] = case_name

            return result


    # --------------------------------------------------------
    # SIMPLE PLURAL
    # --------------------------------------------------------

    if (
        surface.endswith("లు")
        and len(surface) > 3
    ):

        root = surface[:-2]

        result[
            "base_candidates"
        ].append(root)

        result["number"] = "plural"

        return result


    # --------------------------------------------------------
    # SINGULAR CASE
    # --------------------------------------------------------

    for suffix in sorted(
        SINGULAR_CASE_SUFFIXES,
        key=len,
        reverse=True,
    ):

        if (
            surface.endswith(suffix)
            and len(surface)
            > len(suffix) + 1
        ):

            root = surface[
                : -len(suffix)
            ]

            result[
                "base_candidates"
            ].append(root)

            result["case"] = suffix

            return result


    # --------------------------------------------------------
    # ORIGINAL FORM
    # --------------------------------------------------------

    result[
        "base_candidates"
    ].append(surface)

    return result


def generate_nominal_variations(
    base: str,
) -> Dict[str, str]:

    """
    Generate useful surface forms for a known noun.

    This is intentionally limited to regular Telugu grammatical
    patterns.

    It is NOT a replacement for grammar.json.
    """

    base = normalize_word(
        base
    )

    if not base:
        return {}


    variations = {
        "base": base,
        "plural": base + "లు",
        "accusative": base + "ను",
        "dative": base + "కు",
        "locative": base + "లో",
        "instrumental": base + "తో",
    }


    return variations


def build_variation_context(
    entries: List[Dict],
) -> List[Dict]:

    """
    Convert vocabulary entries into compact morphological context
    for the AI.
    """

    result = []


    for entry in entries:

        melimi = str(
            entry.get(
                "melimi",
                "",
            )
        ).strip()

        standard = str(
            entry.get(
                "standard",
                "",
            )
        ).strip()


        if not melimi:
            continue


        result.append(
            {
                "standard": standard,
                "melimi": melimi,
                "variations":
                    generate_nominal_variations(
                        melimi
                    ),
            }
        )


    return result


def find_base_matches(
    surface_word: str,
    vocabulary: List[Dict],
) -> List[Dict]:

    """
    Connect a surface form such as:

        ఎడాటాలను

    to a vocabulary base such as:

        ఎడాటం

    where possible.

    This uses conservative suffix stripping.
    """

    analysis = analyze_surface_form(
        surface_word
    )

    candidates = set(
        analysis[
            "base_candidates"
        ]
    )

    matches = []


    for entry in vocabulary:

        melimi = normalize_word(
            entry.get(
                "melimi",
                "",
            )
        )

        if not melimi:
            continue


        if melimi in candidates:

            matches.append(
                entry
            )
            continue


        # Also accept the dictionary word as the
        # stem when the surface candidate is a
        # close grammatical extension.
        for candidate in candidates:

            if (
                candidate.startswith(
                    melimi
                )
                and len(candidate)
                >= len(melimi)
            ):

                matches.append(
                    entry
                )

                break


    return matches


def analyze_text(
    text: str,
    vocabulary: List[Dict],
) -> List[Dict]:

    """
    Analyze all Telugu words in a text and connect surface forms
    to known Melimi vocabulary.
    """

    results = []


    for word in TELUGU_RE.findall(
        text or ""
    ):

        matches = find_base_matches(
            word,
            vocabulary,
        )


        if matches:

            results.append(
                {
                    "surface": word,
                    "matches": matches,
                }
            )


    return results
