
from typing import Dict, List


# These are intentionally metadata rules, not a fake complete grammar.
# The authoritative grammar remains the curated Melimi corpus/rules.
DERIVATIONAL_MARKERS = {
    "కాను": "agent/property/characterizing derivation",
    "వాను": "having/related-to derivation",
    "మారి": "quality/characteristic derivation",
    "అలవి": "quality/state derivation",
    "అరిది": "quality/state derivation",
    "పాదు": "nominal/derived-form family",
    "అంగి": "derivational family",
    "కము": "abstract/nominal derivation",
    "ఇకము": "abstract/nominal derivation",
    "గము": "derivational family",
    "ఓరు": "derivational family",
    "ఆది": "derivational family",
    "ఓలి": "derivational family",
    "ఓజ": "derivational family",
}


def grammar_policy() -> str:
    lines = [
        "MELIMI GRAMMAR/WORD-FORMATION POLICY:",
        "- Use established Melimi grammar and the supplied corpus as authority.",
        "- Preserve Telugu grammatical roles when expressing a meaning in Melimi.",
        "- Use productive derivation only when the corpus/rule evidence supports it.",
        "- Do not treat every suffix as universally productive.",
        "- Do not invent a derived form merely because a suffix exists.",
    ]
    for suffix, meaning in DERIVATIONAL_MARKERS.items():
        lines.append(f"- {suffix}: {meaning}")
    return "\n".join(lines)


def audit_derivational_surface(text: str) -> List[Dict]:
    return [
        {"form": suffix, "rule": meaning}
        for suffix, meaning in DERIVATIONAL_MARKERS.items()
        if suffix in (text or "")
    ]
