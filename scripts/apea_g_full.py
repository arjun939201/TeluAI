"""Run one approved APEA-G plan continuously from first step to final capability."""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from scripts import apea_g_loop as core

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / ".apea/continuous-plan.json"
STATE_PATH = ROOT / ".apea/continuous-state.json"
MAX_PATCH_RETRIES = 3


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reliable_push(branch: str, message: str) -> str:
    """Push state using git's exit code; the legacy helper compared command output."""
    subprocess.run(["git", "config", "user.name", "APEA-G"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "apea-g@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "--", "."], cwd=ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        raise RuntimeError("step produced no changes")
    if diff.returncode != 1:
        raise RuntimeError("unable to inspect staged APEA-G changes")
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-u", "origin", f"HEAD:{branch}"], cwd=ROOT, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def install_runtime_guards() -> None:
    """Harden the legacy step engine without changing its safety gates."""
    original_provider = core.provider
    original_push = core.push

    def resilient_provider(instruction: str):
        last_error = ""
        for attempt in range(1, MAX_PATCH_RETRIES + 1):
            prompt = instruction
            if last_error:
                prompt += f"\nPREVIOUS OUTPUT WAS REJECTED: {last_error}\nReturn exactly one JSON object only. Do not append commentary, Markdown, multiple JSON objects, or any text after the JSON object. For implementation, return a corrected unified diff with recognized repository file paths."
            try:
                result = original_provider(prompt)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = f"invalid provider JSON: {exc}"
                if attempt < MAX_PATCH_RETRIES:
                    print(f"APEA-G provider output rejected; retry {attempt + 1}/{MAX_PATCH_RETRIES}: {last_error}")
                    continue
                raise RuntimeError(f"APEA-G provider output failed after {MAX_PATCH_RETRIES} attempts: {last_error}") from exc
            patch = result.get("patch") if isinstance(result, dict) else None
            if isinstance(patch, str) and patch.strip():
                report = core.preflight(patch)
                if report.ok:
                    return result
                last_error = "; ".join(report.violations)
            else:
                last_error = "empty or missing patch"
            if attempt < MAX_PATCH_RETRIES:
                print(f"APEA-G patch output rejected; retry {attempt + 1}/{MAX_PATCH_RETRIES}: {last_error}")
        raise RuntimeError(f"APEA-G patch generation failed after {MAX_PATCH_RETRIES} attempts: {last_error}")

    core.provider = resilient_provider
    core.push = reliable_push
    # Branch pushes already create authoritative CI runs; avoid a duplicate dispatch.
    core.dispatch_ci = lambda branch: None


def main() -> int:
    plan = load(PLAN_PATH)
    state = load(STATE_PATH) or {"completed_capabilities": [], "completed": [], "history": []}
    approved = os.environ.get("APEA_PLAN_APPROVED", "false").lower() == "true" or state.get("plan_approved") is True
    if not plan or not plan.get("capabilities"):
        raise RuntimeError("No complete persisted APEA-G plan exists")
    if not approved:
        print(json.dumps({"status": "AWAITING_PLAN_APPROVAL", "capabilities": len(plan["capabilities"])}))
        return 0

    install_runtime_guards()
    state["plan_approved"] = True
    state["status"] = "executing"
    save(STATE_PATH, state)
    branch = state.get("branch") or "apea-g/continuous-boot"

    for item in plan["capabilities"]:
        capability = item["capability"]
        if capability in set(state.get("completed_capabilities", [])):
            continue
        capability_plan = {"capability": capability, "goal": item.get("goal"), "steps": item.get("steps", [])}
        if not capability_plan["steps"]:
            state.setdefault("completed_capabilities", []).append(capability)
            continue
        state["capability"] = capability
        core.execute_capability(capability_plan, state, branch)
        state.setdefault("completed_capabilities", []).append(capability)
        state["completed_capabilities"] = list(dict.fromkeys(state["completed_capabilities"]))
        state["completed"] = []
        state["status"] = "advancing"
        save(STATE_PATH, state)
        reliable_push(branch, f"chore: persist APEA-G {capability} progress")

    state["status"] = "complete"
    save(STATE_PATH, state)
    if core.sh("git", "status", "--porcelain"):
        reliable_push(branch, "chore: persist APEA-G completion state")
    print(json.dumps({"status": "COMPLETE", "capabilities": state.get("completed_capabilities", [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
