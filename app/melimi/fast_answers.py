"""Deterministic answers for tiny, high-confidence Melimi knowledge queries.

These avoid spending a Groq request on questions whose answer is already an
explicit part of the authoritative language contract.
"""

import re


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


MELIMI_DEFINITION = (
    "మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన భాషా రూపం. "
    "ఇందులో కుదిరిన మేలిమి మాటలు, పదనిర్మాణ నియమాలు, పదార్థభేదాలు, "
    "వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం మేలిమి నియమాలతో "
    "పాటు కొనసాగుతుంది."
)


def local_answer(message: str, mode: str) -> str | None:
    if mode != "melimi":
        return None
    key = _key(message)
    if key in {
        "మేలిమి తెలుగు అంటే ఏమిటి?",
        "మేలిమి తెలుగు అంటే ఏమిటి",
        "మేలిమి తెలుగు ఏమిటి?",
        "మేలిమి తెలుగు ఏమిటి",
    }:
        return MELIMI_DEFINITION
    return None
