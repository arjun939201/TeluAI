"""Enforce TeluAI's canonical source-tree boundaries."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# There must be one frontend source tree. The backend serves /static directly.
forbidden = ROOT / "app" / "static"
if forbidden.exists():
    raise SystemExit(f"Forbidden duplicate project tree exists: {forbidden.relative_to(ROOT)}")

print("Project structure checks passed.")
