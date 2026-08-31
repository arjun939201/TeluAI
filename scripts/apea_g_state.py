"""Fail-closed durable state, plan, and roadmap engine for APEA-G."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".apea" / "state.json"
ROADMAP_PATH = ROOT / ".apea" / "roadmap.json"
PLAN_PATH = ROOT / ".apea" / "plan.json"
MAX_HISTORY = 100
MAX_STEPS = 12

DEFAULT_STATE = {
    "schema_version": 3,
    "last_green_sha": None,
    "current_capability": None,
    "capability_status": "unknown",
    "last_action": None,
    "attempt": 0,
    "plan_id": None,
    "current_step": 0,
    "step_status": "idle",
    "repair_attempts": 0,
    "provider_status": "ready",
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


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return _clone(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid APEA-G JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid APEA-G JSON object: {path}")
    return data


def load_state() -> dict[str, Any]:
    data = _load_json(STATE_PATH, DEFAULT_STATE)
    version = data.get("schema_version")
    if version not in (1, 2, 3):
        raise ValueError("invalid APEA-G state schema")
    data.setdefault("history", [])
    if not isinstance(data["history"], list):
        raise ValueError("invalid APEA-G history")
    data["schema_version"] = 3
    for key, value in DEFAULT_STATE.items():
        data.setdefault(key, _clone(value))
    data["history"] = data["history"][-MAX_HISTORY:]
    return data


def load_roadmap() -> dict[str, Any]:
    data = _load_json(ROADMAP_PATH, DEFAULT_ROADMAP)
    if data.get("schema_version") != 1:
        raise ValueError("invalid APEA-G roadmap schema")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or len(capabilities) > 100:
        raise ValueError("invalid APEA-G capabilities")
    if not all(isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"] for x in capabilities):
        raise ValueError("invalid APEA-G capability entry")
    return data


def load_plan() -> dict[str, Any] | None:
    if not PLAN_PATH.exists():
        return None
    data = _load_json(PLAN_PATH, {})
    if data.get("schema_version") != 1:
        raise ValueError("invalid APEA-G plan schema")
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError("invalid APEA-G plan steps")
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("id"), str) or not step["id"]:
            raise ValueError("invalid APEA-G plan step")
    return data


def save_plan(plan: dict[str, Any]) -> None:
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ValueError("invalid APEA-G plan")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError("plan must contain 1-12 steps")
    _atomic_write(PLAN_PATH, plan)


def next_capability(roadmap: dict[str, Any] | None = None) -> str | None:
    roadmap = roadmap or load_roadmap()
    for item in roadmap["capabilities"]:
        if item.get("status") in {"active", "pending"}:
            return str(item["id"])
    return None


def set_capability_status(roadmap: dict[str, Any], capability: str, status: str) -> dict[str, Any]:
    allowed = {"pending", "active", "complete", "blocked"}
    if status not in allowed:
        raise ValueError("invalid capability status")
    found = False
    for item in roadmap["capabilities"]:
        if item.get("id") == capability:
            item["status"] = status
            found = True
            break
    if not found:
        raise ValueError(f"unknown capability: {capability}")
    return roadmap


def save_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema_version") != 1:
        raise ValueError("invalid APEA-G roadmap schema")
    _atomic_write(ROADMAP_PATH, roadmap)


def record(state: dict[str, Any], *, sha: str | None = None, capability: str | None = None, status: str | None = None, action: str | None = None, step: int | None = None, provider_status: str | None = None) -> dict[str, Any]:
    if sha is not None:
        state["last_green_sha"] = sha
    if capability is not None:
        state["current_capability"] = capability
    if status is not None:
        state["capability_status"] = status
    if action is not None:
        state["last_action"] = action
    if step is not None:
        state["current_step"] = int(step)
    if provider_status is not None:
        state["provider_status"] = provider_status
    state["attempt"] = int(state.get("attempt", 0)) + 1
    state.setdefault("history", []).append({
        "sha": sha,
        "capability": capability,
        "status": status,
        "action": action,
        "step": step,
        "provider_status": provider_status,
    })
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def save_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict) or state.get("schema_version") not in (1, 2, 3):
        raise ValueError("invalid APEA-G state")
    state["schema_version"] = 3
    state["history"] = list(state.get("history", []))[-MAX_HISTORY:]
    _atomic_write(STATE_PATH, state)
