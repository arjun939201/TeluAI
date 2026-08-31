"""Continuous APEA-G entrypoint: reconcile CI state and bootstrap the successor loop."""
from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.apea_g_execution_gate import GateAction, decide
import scripts.apea_g as agent

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".apea/state.json"
PLAN_PATH = ROOT / ".apea/plan.json"
ROADMAP_PATH = ROOT / ".apea/roadmap.json"


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return json.loads(json.dumps(default))
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def _unfinished_capabilities() -> list[str]:
    roadmap = _load(ROADMAP_PATH, {"capabilities": []})
    return [str(item["id"]) for item in roadmap.get("capabilities", []) if item.get("status") != "complete"]


def bootstrap_loop_state() -> None:
    """Persist a deterministic cursor for the post-v2 continuous plan loop."""
    if not PLAN_PATH.exists():
        return
    plan = _load(PLAN_PATH, {})
    successor = plan.get("successor_plan")
    if not isinstance(successor, dict):
        return

    state = _load(STATE_PATH, {"schema_version": 3, "history": []})
    state.setdefault("history", [])
    state["schema_version"] = max(int(state.get("schema_version", 1)), 3)

    if not isinstance(state.get("loop"), dict):
        unfinished = _unfinished_capabilities()
        state["loop"] = {
            "plan_id": successor.get("plan_id", "apea-g-loop-v1"),
            "cursor": 0,
            "current_capability": unfinished[0] if unfinished else None,
            "status": "ready" if unfinished else "complete",
            "completed_capabilities": [],
        }
        state["history"].append({
            "action": "loop-bootstrap",
            "plan_id": state["loop"]["plan_id"],
            "current_capability": state["loop"]["current_capability"],
        })
        state["history"] = state["history"][-50:]
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def reconcile_ci_state() -> None:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return
    event = json.loads(Path(event_path).read_text())
    run = event.get("workflow_run") or {}
    conclusion = run.get("conclusion")
    branch = run.get("head_branch") or "main"
    if branch == "main" or conclusion not in {"success", "failure"}:
        return
    if not STATE_PATH.exists():
        return
    state = json.loads(STATE_PATH.read_text())
    status = state.get("step_status")
    if status in {"in_progress", "ci_pending", "repairing"}:
        decision = decide(
            ci_conclusion=conclusion,
            step_status="ci_pending",
            repair_attempts=int(state.get("repair_attempts", 0)),
        )
        if decision.action in {GateAction.ADVANCE, GateAction.REPAIR}:
            state["step_status"] = "ci_pending"
            state["last_ci_conclusion"] = conclusion
            state["last_ci_run_id"] = run.get("id")
            STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        elif decision.action is GateAction.BLOCK:
            state["step_status"] = "blocked"
            state["blocked_reason"] = decision.reason
            STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    bootstrap_loop_state()
    reconcile_ci_state()
    raise SystemExit(agent.main())
