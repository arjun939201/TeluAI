"""Build and persist the complete APEA-G roadmap plan before execution."""
from __future__ import annotations
import json
from pathlib import Path
from scripts import apea_g_loop as core

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / ".apea/continuous-plan.json"
STATE_PATH = ROOT / ".apea/continuous-state.json"


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    existing = load(PLAN_PATH)
    if existing and existing.get("status") in {"awaiting_approval", "approved", "executing", "complete"}:
        print(json.dumps({"status": "EXISTING_PLAN", "capabilities": len(existing.get("capabilities", []))}))
        return 0

    state = load(STATE_PATH) or {"completed_capabilities": [], "completed": [], "history": []}
    completed = set(state.get("completed_capabilities", []))
    capabilities = []
    for item in core.roadmap().get("capabilities", []):
        cid = str(item.get("id"))
        if cid in completed or item.get("status") in {"complete", "cancelled"}:
            continue
        plan = core.make_capability_plan(cid)
        capabilities.append({
            "capability": cid,
            "goal": plan.get("goal"),
            "steps": plan.get("steps", [])[:core.MAX_STEPS],
        })

    if not capabilities:
        full = {"schema_version": 1, "status": "complete", "approval_required": False, "capabilities": []}
    else:
        full = {
            "schema_version": 1,
            "status": "awaiting_approval",
            "approval_required": True,
            "generated_from": ".apea/roadmap.json",
            "capabilities": capabilities,
        }
    save(PLAN_PATH, full)
    state["status"] = "awaiting_plan_approval" if capabilities else "complete"
    state["plan_approved"] = False
    state["plan_capabilities"] = [item["capability"] for item in capabilities]
    save(STATE_PATH, state)
    if capabilities:
        head = core.push(state.get("branch") or "apea-g/continuous-boot", "chore: persist complete APEA-G execution plan")
        print(json.dumps({"status": "PLAN_READY", "commit": head, "capabilities": len(capabilities), "plan": full}))
    else:
        print(json.dumps({"status": "COMPLETE", "plan": full}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
