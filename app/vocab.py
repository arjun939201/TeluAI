import json
import os
from typing import List, Dict

from app.config import settings


def _load_json(filename: str):
    path = os.path.join(settings.DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


VOCABULARY: List[Dict] = _load_json("vocabulary.json")
EXAMPLES: List[Dict] = _load_json("examples.json")


def retrieve_vocab(message: str, limit: int = None) -> List[Dict]:
    """Return vocabulary entries whose standard-Telugu word/phrase appears in
    the user's message. Simple substring match - swap for SQLite LIKE or a
    local embedding search if your vocab file grows into the thousands."""
    limit = limit or settings.MAX_VOCAB_MATCHES
    matches = [entry for entry in VOCABULARY if entry["standard"] in message]
    return matches[:limit]


def get_examples(limit: int = None) -> List[Dict]:
    limit = limit or settings.MAX_EXAMPLES
    return EXAMPLES[:limit]
