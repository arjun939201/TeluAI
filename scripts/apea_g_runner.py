"""Continuous APEA-G entrypoint: reconcile CI state before invoking the agent."""
from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.apea_g_execution_gate import GateAction, decide
import scripts.apea_g as agent

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".apea/state.json"


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
    reconcile_ci_state()
    raise SystemExit(agent.main())
