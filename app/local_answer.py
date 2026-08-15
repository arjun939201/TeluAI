"""Tier 0 of the local-first pipeline: answer simple, unambiguous
'X అంటే ఏమిటి?' (what does X mean?) questions entirely from local knowledge —
the DB-approved mapping table first, then the existing vocabulary.json /
melimi corpus lookups — without spending any Groq tokens at all.

This intentionally only handles the narrow, high-confidence case: a short
message that is *only* a definition question about a single known term, with
no prior conversation history (so there's no context that could change the
intended meaning). Anything else falls through to the normal pipeline.
"""

from __future__ import annotations

import re
from typing import Optional

from app.retrieval.knowledge import load_vocabulary, norm

DEFINITION_RE = re.compile(
    r"^([\u0C00-\u0C7F][\u0C00-\u0C7F\s]{0,40}?)\s*అంటే\s*(?:ఏమిటి|ఏమి|ఏంటి)\s*[?？]?\s*$"
)


def _find_local_pair(term: str) -> Optional[dict]:
    term_n = norm(term)
    for entry in load_vocabulary():
        if norm(entry.get("standard", "")) == term_n or norm(entry.get("melimi", "")) == term_n:
            return {
                "standard": entry.get("standard", ""),
                "melimi": entry.get("melimi", ""),
                "note": entry.get("note", ""),
            }

    try:
        from app.melimi.registry import lexical_inventory

        inv = lexical_inventory()
        std_to_mel = inv.get("standard_to_melimi", {})
        mel_to_std = inv.get("melimi_to_standard", {})
        if term in std_to_mel:
            return {"standard": term, "melimi": std_to_mel[term], "note": ""}
        if term in mel_to_std:
            return {"standard": mel_to_std[term], "melimi": term, "note": ""}
    except Exception:
        pass

    return None


async def try_deterministic_answer(message: str, mode: str, history_len: int) -> Optional[str]:
    """Return a locally-composed answer, or None to fall through to Groq."""
    if mode != "melimi" or history_len > 0:
        return None

    match = DEFINITION_RE.match((message or "").strip())
    if not match:
        return None

    term = match.group(1).strip()
    if not term:
        return None

    pair = None
    try:
        from app.db import repository as db_repo

        pair = await db_repo.lookup_approved(term)
    except Exception:
        pair = None

    if pair is None:
        pair = _find_local_pair(term)

    if pair is None:
        return None

    standard = pair.get("standard") or term
    melimi = pair.get("melimi") or ""
    detail = pair.get("note") or pair.get("meaning") or ""
    if not melimi:
        return None

    reply = f'{standard} ని మేలిమి తెలుగులో "{melimi}" అంటారు.'
    if detail:
        reply += f" ({detail})"
    return reply
