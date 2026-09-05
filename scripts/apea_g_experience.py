"""Persistent, bounded experience learning for APEA-G."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIENCE_DIR = ROOT / ".apea" / "experience"
OUTCOMES_PATH = EXPERIENCE_DIR / "outcomes.jsonl"
STRATEGIES_PATH = EXPERIENCE_DIR / "strategies.json"
LESSONS_PATH = EXPERIENCE_DIR / "lessons.jsonl"
MAX_LESSONS = 500


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def record_outcome(*, capability: str, step: str, outcome: str, commit: str | None = None,
                   ci: dict[str, Any] | None = None, action: str | None = None,
                   diagnosis: str | None = None, repair_attempt: int = 0) -> dict[str, Any]:
    """Record a secret-free execution outcome and update bounded strategy statistics."""
    ci = ci or {}
    failure = ci.get("failure") or {}
    record = {
        "timestamp": int(time.time()),
        "capability": capability,
        "step": step,
        "outcome": outcome,
        "commit": commit,
        "ci_run_id": ci.get("run_id"),
        "ci_conclusion": ci.get("conclusion"),
        "failure_kind": failure.get("kind"),
        "failure_signature": failure.get("signature"),
        "action": action,
        "repair_attempt": repair_attempt,
    }
    _append(OUTCOMES_PATH, record)

    if action:
        strategies = _load_json(STRATEGIES_PATH, {})
        entry = strategies.setdefault(action, {"attempts": 0, "successes": 0, "failures": 0})
        entry["attempts"] += 1
        if outcome in {"success", "repaired"}:
            entry["successes"] += 1
        elif outcome in {"failure", "repair_failed"}:
            entry["failures"] += 1
        entry["confidence"] = round(entry["successes"] / entry["attempts"], 4)
        entry["updated_at"] = int(time.time())
        save_json(STRATEGIES_PATH, strategies)

    if outcome in {"success", "repaired", "repair_failed", "blocked"}:
        lesson = {
            "timestamp": record["timestamp"],
            "capability": capability,
            "step": step,
            "outcome": outcome,
            "failure_kind": failure.get("kind"),
            "failure_signature": failure.get("signature"),
            "action": action,
            "diagnosis": diagnosis,
            "commit": commit,
        }
        _append(LESSONS_PATH, lesson)
    return record


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recent_experience(*, capability: str | None = None, failure_signature: str | None = None,
                      limit: int = 8) -> list[dict[str, Any]]:
    """Retrieve recent relevant experience without exposing raw CI logs."""
    if not OUTCOMES_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = OUTCOMES_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if capability and item.get("capability") != capability:
            continue
        if failure_signature and item.get("failure_signature") != failure_signature:
            continue
        records.append(item)
        if len(records) >= limit:
            break
    return records


def best_strategy(action_candidates: list[str], *, capability: str | None = None) -> dict[str, Any] | None:
    """Choose a learned strategy, preferring relevant successful history."""
    strategies = _load_json(STRATEGIES_PATH, {})
    scored = []
    for action in action_candidates:
        item = strategies.get(action, {})
        attempts = int(item.get("attempts", 0))
        successes = int(item.get("successes", 0))
        confidence = float(item.get("confidence", 0.0)) if attempts else 0.0
        history = recent_experience(capability=capability, limit=20)
        relevant_successes = sum(1 for row in history if row.get("action") == action and row.get("outcome") in {"success", "repaired"})
        scored.append((confidence, relevant_successes, -int(item.get("failures", 0)), action, attempts))
    if not scored:
        return None
    confidence, relevant, _, action, attempts = max(scored)
    return {"action": action, "confidence": confidence, "relevant_successes": relevant, "attempts": attempts}


def render_context(*, capability: str, failure_signature: str | None = None) -> str:
    """Return compact learning context suitable for an LLM prompt."""
    rows = recent_experience(capability=capability, failure_signature=failure_signature, limit=6)
    strategy = best_strategy(
        ["repair_contract", "repair_fixture", "repair", "repair_workflow", "retry_ci", "diagnose"],
        capability=capability,
    )
    return json.dumps({"recent": rows, "preferred_strategy": strategy}, ensure_ascii=False)
