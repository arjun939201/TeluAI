"""Deterministic pre-commit validation for the APEA-G engineering controller.

The gate is intentionally provider-free: it validates the proposed repository
change using Git metadata and repository contracts before APEA-G spends a CI
run or asks an LLM to repair anything.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import fnmatch
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNERSHIP_PATH = ROOT / ".apea/contracts/ownership.json"


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    risk: str
    changed_files: tuple[str, ...]
    affected_subsystems: tuple[str, ...]
    focused_tests: tuple[str, ...]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def changed_files(*, staged: bool = False) -> tuple[str, ...]:
    args = ["diff", "--name-only", "--diff-filter=ACMR"]
    if staged:
        args.insert(1, "--cached")
    else:
        args.extend(["HEAD", "--"])
    return tuple(path for path in _git(*args).splitlines() if path)


def load_ownership() -> dict[str, object]:
    data = json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported ownership contract schema")
    if not isinstance(data.get("subsystems"), list):
        raise ValueError("ownership contract must define subsystems")
    return data


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.endswith("/") and path.startswith(pattern)
    )


def affected_subsystems(files: tuple[str, ...], ownership: dict[str, object]) -> tuple[str, ...]:
    found: list[str] = []
    for subsystem in ownership["subsystems"]:
        paths = subsystem.get("paths", [])
        if any(_matches(path, pattern) for path in files for pattern in paths):
            found.append(str(subsystem["id"]))
    return tuple(dict.fromkeys(found))


def focused_tests(files: tuple[str, ...], ownership: dict[str, object]) -> tuple[str, ...]:
    tests: list[str] = []
    for subsystem in ownership["subsystems"]:
        if any(_matches(path, pattern) for path in files for pattern in subsystem.get("paths", [])):
            tests.extend(str(item) for item in subsystem.get("tests", []))
    return tuple(dict.fromkeys(tests))


def _validate_json_contracts(files: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    candidates = {path for path in files if path.startswith(".apea/") and path.endswith(".json")}
    candidates.add(".apea/contracts/ownership.json")
    for relative in sorted(candidates):
        path = ROOT / relative
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON contract {relative}: {exc}")
    return errors


def run(files: tuple[str, ...] | None = None, *, staged: bool = False) -> PreflightResult:
    files = tuple(files) if files is not None else changed_files(staged=staged)
    errors: list[str] = []
    try:
        ownership = load_ownership()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return PreflightResult(False, "high", files, (), (), (f"ownership contract unavailable: {exc}",))

    protected = tuple(str(item) for item in ownership.get("protected_paths", []))
    touched_protected = tuple(path for path in files if any(_matches(path, pattern) for pattern in protected))
    if touched_protected:
        errors.append("protected control paths changed: " + ", ".join(touched_protected))

    errors.extend(_validate_json_contracts(files))
    subsystems = affected_subsystems(files, ownership)
    tests = focused_tests(files, ownership)
    high_risk = set(str(item) for item in ownership.get("high_risk_subsystems", []))
    risk = "high" if any(item in high_risk for item in subsystems) or touched_protected else "medium" if len(files) > 8 else "low"
    return PreflightResult(not errors, risk, files, subsystems, tests, tuple(errors))


def main() -> int:
    result = run()
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
