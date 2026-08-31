"""Small, fail-closed durable state store for APEA-G engineering progress."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".apea" / "state.json"
MAX_HISTORY = 50


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"schema_version": 1, "last_green_sha": None, "current_capability": None, "capability_status": "unknown", "last_action": None, "attempt": 0, "history": []}
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("invalid APEA-G state")
    history = data.get("history", [])
    if not isinstance(history, list):
        raise ValueError("invalid APEA-G history")
    data["history"] = history[-MAX_HISTORY:]
    return data


def record(state: dict[str, Any], *, sha: str | None = None, capability: str | None = None, status: str | None = None, action: str | None = None) -> dict[str, Any]:
    if sha is not None:
        state["last_green_sha"] = sha
    if capability is not None:
        state["current_capability"] = capability
    if status is not None:
        state["capability_status"] = status
    if action is not None:
        state["last_action"] = action
    state["attempt"] = int(state.get("attempt", 0)) + 1
    state.setdefault("history", []).append({"sha": sha, "capability": capability, "status": status, "action": action})
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
