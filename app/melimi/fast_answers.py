"""Deterministic high-confidence answers for the Melimi runtime."""

import re


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().casefold())


MELIMI_DEFINITION = (
    "మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన భాషా రూపం. "
    "ఇందులో కుదిరిన మేలిమి మాటలు, పదనిర్మాణ నియమాలు, పదార్థభేదాలు, "
    "వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం మేలిమి నియమాలతో "
    "పాటు కొనసాగుతుంది."
)

GREETING = "నమస్కారం, ఏవైనా ఆసక్తికరమైన విషయాలు పంచుకోవాలని అనుకుంటున్నారా?"


def local_answer(message: str, mode: str) -> str | None:
    if mode != "melimi":
        return None

    key = _key(message)
    if key in {
        "hi", "hello", "hey", "నమస్కారం", "టేంకణం",
    }:
        # Keep this response in the neutral Telugu layer. The deterministic
        # Melimi vocabulary runtime performs the established lexical rendering.
        return GREETING

    if key in {
        "మేలిమి తెలుగు అంటే ఏమిటి?",
        "మేలిమి తెలుగు అంటే ఏమిటి",
        "మేలిమి తెలుగు ఏమిటి?",
        "మేలిమి తెలుగు ఏమిటి",
    }:
        return MELIMI_DEFINITION

    return None
