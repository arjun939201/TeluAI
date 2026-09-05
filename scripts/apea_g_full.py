"""Run one approved APEA-G plan continuously from first step to final capability."""
from __future__ import annotations
import json
import os
from pathlib import Path
from scripts import apea_g_loop as core

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / ".apea/continuous-plan.json"
STATE_PATH = ROOT / ".apea/continuous-state.json"

def load(path: Path):
    try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError): return None

def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    plan = load(PLAN_PATH); state = load(STATE_PATH) or {"completed_capabilities": [], "completed": [], "history": []}
    approved = os.environ.get("APEA_PLAN_APPROVED", "false").lower() == "true" or state.get("plan_approved") is True
    if not plan or not plan.get("capabilities"): raise RuntimeError("No complete persisted APEA-G plan exists")
    if not approved:
        print(json.dumps({"status": "AWAITING_PLAN_APPROVAL", "capabilities": len(plan["capabilities"])})); return 0
    state["plan_approved"] = True; state["status"] = "executing"; save(STATE_PATH, state)
    branch = state.get("branch") or "apea-g/continuous-boot"
    for item in plan["capabilities"]:
        capability = item["capability"]
        if capability in set(state.get("completed_capabilities", [])): continue
        capability_plan = {"capability": capability, "goal": item.get("goal"), "steps": item.get("steps", [])}
        if not capability_plan["steps"]:
            state.setdefault("completed_capabilities", []).append(capability); continue
        state["capability"] = capability
        core.execute_capability(capability_plan, state, branch)
        state.setdefault("completed_capabilities", []).append(capability)
        state["completed_capabilities"] = list(dict.fromkeys(state["completed_capabilities"]))
        state["completed"] = []; state["status"] = "advancing"; save(STATE_PATH, state)
    state["status"] = "complete"; save(STATE_PATH, state)
    if core.sh("git", "status", "--porcelain"): core.push(branch, "chore: persist APEA-G completion state")
    print(json.dumps({"status": "COMPLETE", "capabilities": state.get("completed_capabilities", [])})); return 0

if __name__ == "__main__": raise SystemExit(main())
