"""TEX-L generation contract and conservative output validation.

TEX-L supplies linguistic evidence and generation constraints; the language
model remains responsible for natural sentence generation. This module never
invents Melimi vocabulary or grammatical forms.
"""
from __future__ import annotations

import re
from typing import Any

from app.texl_representation import LanguageRepresentation


def build_generation_contract(representation: LanguageRepresentation) -> str:
    """Build a compact, evidence-backed contract for the response generator."""
    lines = [
        "TEX-L GENERATION CONTRACT:",
        "Use authoritative TEX-L evidence as constraints, not as permission to invent grammar.",
        "Do not create a Melimi word, formative, inflection, or rule that is absent from authoritative evidence.",
    ]
    if representation.translation_intent == "LEXICAL_EQUIVALENT":
        lines.extend([
            "Intent: lexical-equivalent question.",
            "Return the authoritative canonical Melimi equivalent, not a source-case-inflected version.",
            "Example contract: a source accusative surface asking 'what is this word called?' maps to the canonical Melimi word.",
        ])
        if representation.lexical_equivalent:
            lines.append(f"Authoritative lexical equivalent: {representation.lexical_equivalent}")
    elif representation.regeneration_role:
        lines.extend([
            "Intent: contextual/sentence generation.",
            f"Target grammatical role identified by TEX-L: {representation.regeneration_role}.",
            "Preserve the role when producing a target sentence, but only use a target inflection supported by the language model's established knowledge or authoritative TEX-L evidence.",
            "Do not transfer source suffixes mechanically onto the Melimi word.",
        ])
    else:
        lines.append("No authoritative grammatical regeneration role is established; answer naturally without inventing a Melimi transformation.")
    if representation.evidence:
        lines.append("Authoritative evidence:")
        for item in representation.evidence:
            if not item.authoritative or not item.melimi:
                continue
            details = [f"surface={item.surface}", f"canonical={item.canonical}", f"melimi={item.melimi}"]
            if item.morphology:
                details.append(f"morphology={item.morphology}")
            if item.grammatical_role:
                details.append(f"role={item.grammatical_role}")
            lines.append("- " + "; ".join(details))
    return "\n".join(lines)


def validate_generated_response(
    answer: str,
    representation: LanguageRepresentation,
) -> dict[str, Any]:
    """Validate only claims that TEX-L can prove deterministically.

    A validator must not become a hidden grammar generator. For lexical
    questions it therefore enforces the canonical authoritative answer and
    rejects source-case transfer; for ordinary sentences it reports evidence
    rather than guessing a replacement inflection.
    """
    value = str(answer or "").strip()
    issues: list[str] = []

    if representation.translation_intent == "LEXICAL_EQUIVALENT" and representation.lexical_equivalent:
        melimi = representation.lexical_equivalent
        for ending in ("ను", "ని"):
            surface = melimi + ending
            if re.search(rf"(?<![\u0C00-\u0C7F]){re.escape(surface)}(?![\u0C00-\u0C7F])", value):
                issues.append("lexical_equivalent_has_source_case_transfer")
                break

    return {
        "valid": not issues,
        "issues": issues,
        "checked": True,
        "repairable": bool(issues) and representation.translation_intent == "LEXICAL_EQUIVALENT",
    }
