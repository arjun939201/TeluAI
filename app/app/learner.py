
"""Controlled learning helpers.

New material is stored as candidate evidence rather than silently becoming
authoritative vocabulary. The authoritative corpus remains vocabulary.json.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATE_FILE = os.path.join(BASE, "data", "learning_candidates.json")


def _load() -> List[Dict[str, Any]]:
    if not os.path.exists(CANDIDATE_FILE):
        return []
    try:
        with open(CANDIDATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def learn_text(text: str, document_id: str = "user_text") -> Dict[str, Any]:
    candidates = _load()
    item = {
        "status": "candidate",
        "document_id": document_id,
        "text": text.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    candidates.append(item)
    os.makedirs(os.path.dirname(CANDIDATE_FILE), exist_ok=True)
    with open(CANDIDATE_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    return {"added": True, "status": "candidate", "message": "Stored as a learning candidate."}


def build_learned_context(message: str, limit: int = 4, max_chars: int = 1600) -> str:
    # Candidate material is intentionally not injected into normal chat by default.
    return ""
