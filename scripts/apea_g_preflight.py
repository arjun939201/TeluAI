"""Deterministic semantic preflight gate for APEA-G proposed patches."""
from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNERSHIP_PATH = ROOT / ".apea/contracts/ownership.json"
PROTECTED = (
    ".github/workflows/apea-g.yml",
    ".github/workflows/apea-g-continuous.yml",
    "scripts/apea_g.py",
    "scripts/apea_g_loop.py",
    "scripts/apea_g_preflight.py",
    ".env",
    "credentials",
    "secrets",
    "id_rsa",
)


@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    changed_paths: tuple[str, ...]
    affected_areas: tuple[str, ...]
    affected_tests: tuple[str, ...]
    risk: str
    violations: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "changed_paths": list(self.changed_paths),
            "affected_areas": list(self.affected_areas),
            "affected_tests": list(self.affected_tests),
            "risk": self.risk,
            "violations": list(self.violations),
        }


def patch_paths(patch: str) -> tuple[str, ...]:
    paths = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path != "/dev/null":
                paths.append(path)
        elif line.startswith("--- a/") and "+++ b/" not in patch:
            path = line[6:].strip()
            if path != "/dev/null":
                paths.append(path)
    return tuple(dict.fromkeys(paths))


def _protected(path: str) -> bool:
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in PROTECTED)


def _load_ownership() -> dict[str, object]:
    return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))


def _matches(path: str, pattern: str) -> bool:
    return path == pattern or path.startswith(pattern) or fnmatch.fnmatch(path, pattern)


def preflight(patch: str) -> PreflightReport:
    violations: list[str] = []
    paths = patch_paths(patch)
    if not patch.strip():
        violations.append("empty patch")
    if len(patch) > 16000:
        violations.append("patch exceeds autonomous size limit")
    if not paths:
        violations.append("patch contains no recognized file paths")

    affected: set[str] = set()
    tests: set[str] = set()
    ownership = _load_ownership()
    areas = ownership.get("areas", {})
    for path in paths:
        if _protected(path):
            violations.append(f"protected path: {path}")
        if path.startswith(".apea/"):
            violations.append(f"control-plane path: {path}")
        for area, config in areas.items():
            patterns = config.get("paths", [])
            if any(_matches(path, pattern) for pattern in patterns):
                affected.add(area)
                tests.update(config.get("tests", []))

    risk = "low"
    if len(paths) > 4 or len(affected) > 1:
        risk = "medium"
    if any(path.startswith(("app/auth", "app/security", ".github/", "render.yaml")) for path in paths):
        risk = "high"
    if violations:
        risk = "blocked"

    return PreflightReport(
        ok=not violations,
        changed_paths=paths,
        affected_areas=tuple(sorted(affected)),
        affected_tests=tuple(sorted(tests)),
        risk=risk,
        violations=tuple(violations),
    )


def main() -> int:
    import sys

    patch = sys.stdin.read()
    report = preflight(patch)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
