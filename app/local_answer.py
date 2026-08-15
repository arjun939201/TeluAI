"""Deterministic answers that require no Groq call."""
from __future__ import annotations
import re
from app.melimi.root_morphology import convert_text, load_root_dictionary
from app.melimi.registry import lexical_inventory


def answer(message: str, mode: str) -> str | None:
    if mode != "melimi":
        return None
    q = re.sub(r"\s+", " ", (message or "").strip())
    if q in {"మేలిమి తెలుగు అంటే ఏమిటి?", "మేలిమి తెలుగు అంటే ఏమిటి"}:
        return ("మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన నుడి రూపం. ఇందులో కుదిరిన మేలిమి మాటలు, "
                "పదనిర్మాణ నియమాలు, పదార్థభేదాలు, వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం "
                "మేలిమి నియమాలతో పాటు కొనసాగుతుంది.")
    # Direct vocabulary questions: exact Melimi lookup first.
    # The Melimi system is the lens; the answer remains natural Telugu.
    m = re.search(r"^(.+?)(?:\s+అనే\s+(?:పలుకు|పలుక్కు|మాట))?\s+(?:తెల్లం|అర్థం)\s+ఏమిటి\??$", q)
    if not m:
        m = re.fullmatch(r"(.+?)\s*(?:అంటే ఏమిటి|అర్థం ఏమిటి)\??", q)
    if m:
        word = m.group(1).strip()
        word = re.sub(r"\s+అనే\s+(?:పలుకు|పలుక్కు|మాట)$", "", word).strip()
        inv = lexical_inventory()
        standard = inv["melimi_to_standard"].get(word)
        if standard:
            return f"{word} అంటే {standard}."
        roots = load_root_dictionary()
        if word in roots:
            return f"{word}కు మేలిమి తెలుగు మాట: {roots[word]}."
    return None
