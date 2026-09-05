"""Build and persist the complete APEA-G roadmap plan before execution."""
from __future__ import annotations
import json
import subprocess
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


def persist_plan(branch: str) -> str:
    """Commit generated plan/state using git's exit status, not command output."""
    subprocess.run(["git", "config", "user.name", "APEA-G"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "apea-g@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "--", ".apea/continuous-plan.json", ".apea/continuous-state.json"], cwd=ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        return core.sh("git", "rev-parse", "HEAD")
    if diff.returncode != 1:
        raise RuntimeError("unable to inspect generated APEA-G plan changes")
    subprocess.run(["git", "commit", "-m", "chore: persist complete APEA-G execution plan"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-u", "origin", f"HEAD:{branch}"], cwd=ROOT, check=True)
    return core.sh("git", "rev-parse", "HEAD")


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
        capabilities.append({"capability": cid, "goal": plan.get("goal"), "steps": plan.get("steps", [])[:core.MAX_STEPS]})
    full = {"schema_version": 1, "status": "awaiting_approval" if capabilities else "complete", "approval_required": bool(capabilities), "generated_from": ".apea/roadmap.json", "capabilities": capabilities}
    save(PLAN_PATH, full)
    state["status"] = "awaiting_plan_approval" if capabilities else "complete"
    state["plan_approved"] = False
    state["plan_capabilities"] = [item["capability"] for item in capabilities]
    save(STATE_PATH, state)
    if capabilities:
        head = persist_plan(state.get("branch") or "apea-g/continuous-boot")
        print(json.dumps({"status": "PLAN_READY", "commit": head, "capabilities": len(capabilities), "plan": full}))
    else:
        print(json.dumps({"status": "COMPLETE", "plan": full}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
