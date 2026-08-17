"""Enforce TeluAI's canonical source-tree boundaries."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    ROOT / "app" / "static",
)

for path in FORBIDDEN:
    if path.exists():
        raise SystemExit(f"Forbidden duplicate project tree exists: {path.relative_to(ROOT)}")

# Keep these conceptual areas under their canonical packages.
legacy_top_level = (
    ROOT / "app" / "melimi_engine.py",
    ROOT / "app" / "morphology.py",
)
for path in legacy_top_level:
    if path.exists():
        raise SystemExit(
            f"Legacy Melimi module remains outside app/melimi/: {path.relative_to(ROOT)}"
        )

print("Project structure checks passed.")
