"""Detects when a user is *teaching* a Standard<->Melimi word mapping in
chat (e.g. "సహాయం = బాసట" or "సహాయం ని బాసట అంటారు"), so it can be captured
as a pending learning candidate for human review.

This is intentionally conservative and pattern-based — it never writes
directly into the corpus. See app/db/repository.propose_candidate and the
/admin/learning/* endpoints for the approval workflow. A false positive here
just creates a pending row an admin will reject; a false negative just means
the mapping isn't captured automatically and the person can still use the
existing manual /melimi/register flow.
"""

from __future__ import annotations

import re
from typing import Optional

_TELUGU_WORD = r"[\u0C00-\u0C7F]+(?:\s[\u0C00-\u0C7F]+){0,2}"

_EQUALS_RE = re.compile(rf"({_TELUGU_WORD})\s*[=:]\s*({_TELUGU_WORD})")
_CALL_RE = re.compile(rf"({_TELUGU_WORD})\s*(?:ని|ను)\s*({_TELUGU_WORD})\s*అంటార[ుి]")
_MEANS_RE = re.compile(rf"^({_TELUGU_WORD})\s*అంటే\s*({_TELUGU_WORD})\s*$")

# Question markers rule a message out — "X అంటే ఏమిటి?" is a *question*,
# not a *statement* teaching a new mapping.
_QUESTION_MARKERS = ("ఏమిటి", "ఏమి ", "ఏంటి", "ఎలా", "ఎందుకు", "?", "？")


def detect_teaching(message: str) -> Optional[dict]:
    text = (message or "").strip()
    if not text or any(marker in text for marker in _QUESTION_MARKERS):
        return None

    for pattern in (_EQUALS_RE, _CALL_RE, _MEANS_RE):
        match = pattern.search(text) if pattern is not _MEANS_RE else pattern.match(text)
        if match:
            standard = match.group(1).strip()
            melimi = match.group(2).strip()
            if standard and melimi and standard != melimi:
                return {"standard_root": standard, "melimi_root": melimi}

    return None
