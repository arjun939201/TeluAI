"""Fail-closed durable state and roadmap engine for APEA-G."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".apea" / "state.json"
ROADMAP_PATH = ROOT / ".apea" / "roadmap.json"
MAX_HISTORY = 50

DEFAULT_STATE = {
    "schema_version": 2,
    "last_green_sha": None,
    "current_capability": None,
    "capability_status": "unknown",
    "last_action": None,
    "attempt": 0,
    "history": [],
}

DEFAULT_ROADMAP = {
    "schema_version": 1,
    "capabilities": [
        {"id": "foundation", "status": "complete"},
        {"id": "language-brain", "status": "complete"},
        {"id": "melimi", "status": "complete"},
        {"id": "conversation-intelligence", "status": "complete"},
        {"id": "learning-system", "status": "complete"},
        {"id": "response-intelligence", "status": "complete"},
        {"id": "quality-evaluation", "status": "active"},
        {"id": "performance", "status": "pending"},
        {"id": "security", "status": "pending"},
        {"id": "ux", "status": "pending"},
        {"id": "production", "status": "pending"},
        {"id": "release", "status": "pending"},
    ],
}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") not in (1, 2):
        raise ValueError("invalid APEA-G state")
    data.setdefault("history", [])
    if not isinstance(data["history"], list):
        raise ValueError("invalid APEA-G history")
    data["schema_version"] = 2
    data["history"] = data["history"][-MAX_HISTORY:]
    return data


def load_roadmap() -> dict[str, Any]:
    if not ROADMAP_PATH.exists():
        return json.loads(json.dumps(DEFAULT_ROADMAP))
    data = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("invalid APEA-G roadmap")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not all(isinstance(x, dict) and x.get("id") for x in capabilities):
        raise ValueError("invalid APEA-G capabilities")
    return data


def next_capability(roadmap: dict[str, Any]) -> str | None:
    for item in roadmap["capabilities"]:
        if item.get("status") in {"active", "pending"}:
            return str(item["id"])
    return None


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
