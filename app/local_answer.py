"""Deterministic answers that require no Groq call."""
from __future__ import annotations
import re
from app.melimi.root_morphology import convert_text, load_root_dictionary


def answer(message: str, mode: str) -> str | None:
    if mode != "melimi":
        return None
    q = re.sub(r"\s+", " ", (message or "").strip())
    if q in {"మేలిమి తెలుగు అంటే ఏమిటి?", "మేలిమి తెలుగు అంటే ఏమిటి"}:
        return ("మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన నుడి రూపం. ఇందులో కుదిరిన మేలిమి మాటలు, "
                "పదనిర్మాణ నియమాలు, పదార్థభేదాలు, వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం "
                "మేలిమి నియమాలతో పాటు కొనసాగుతుంది.")
    # Direct known root/translation questions can be answered locally.
    m = re.fullmatch(r"(.+?)\s*(?:అంటే ఏమిటి|అర్థం ఏమిటి)\??", q)
    if m:
        root = m.group(1).strip()
        roots = load_root_dictionary()
        if root in roots:
            return f"{root}కు మేలిమి తెలుగు మాట: {roots[root]}."
    return None
