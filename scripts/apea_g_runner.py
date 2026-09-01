"""APEA-G autonomous entrypoint.

The GitHub Actions workflow is the durable scheduler; this entrypoint delegates
execution to the persistent continuous controller. The controller owns planning,
commit/CI verification, evidence-based repair, and advancement.
"""
from __future__ import annotations

import sys
from pathlib import Path

# The workflow invokes this file directly. In that mode Python puts ``scripts``
# (not the repository root) on sys.path, so importing ``scripts`` is not
# portable unless scripts is installed as a package. Import the controller from
# its actual directory instead.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import apea_g_loop  # noqa: E402


def main() -> int:
    return apea_g_loop.main()


if __name__ == "__main__":
    raise SystemExit(main())
