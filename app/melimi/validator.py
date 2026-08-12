
from typing import Dict, List

from app.retrieval.knowledge import load_vocabulary, norm


def known_alternatives(text: str) -> List[Dict]:
    value = norm(text)
    found = []
    for entry in load_vocabulary():
        standard = norm(entry.get("standard", ""))
        melimi = str(entry.get("melimi", "")).strip()
        if standard and melimi and standard in value and melimi not in value:
            found.append({
                "standard": entry.get("standard"),
                "melimi": entry.get("melimi"),
            })
    return found


def audit_melimi(text: str) -> Dict:
    alternatives = known_alternatives(text)
    return {
        "melimi_mode": True,
        "possible_standard_terms": len(alternatives),
        "items": alternatives[:15],
        "needs_review": bool(alternatives),
        "note": (
            "This is an audit signal, not automatic replacement. "
            "The model must preserve grammar and meaning."
        ),
    }


def purity_instruction() -> str:
    return (
        "After composing the answer, silently scan it for Standard/loan vocabulary "
        "where an established Melimi equivalent is available. Replace only when the "
        "replacement preserves meaning and grammar. Do not invent unsupported words."
    )
