"""A cheap fingerprint of TeluAI's local knowledge (vocabulary.json + the
melimi_telugu/ corpus). Used as part of the response-cache key so a cached
Groq answer automatically stops being served the moment the underlying
language knowledge changes (e.g. after an admin approves a new word).

Only file stat() calls (mtime + size), never file contents, so this is fast
enough to call on every request.
"""

from __future__ import annotations

import hashlib
import os


def _fingerprint(path: str) -> str:
    try:
        stat = os.stat(path)
        return f"{path}:{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        return f"{path}:missing"


def knowledge_version() -> str:
    from app.melimi.index import SUBJECT
    from app.retrieval.knowledge import VOCAB_FILE

    parts = [_fingerprint(VOCAB_FILE)]
    if SUBJECT.exists():
        for path in sorted(SUBJECT.rglob("*")):
            if path.is_file():
                parts.append(_fingerprint(str(path)))

    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]
