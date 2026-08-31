"""APEA-G autonomous entrypoint.

The GitHub Actions workflow is the durable scheduler; this entrypoint delegates
execution to the persistent continuous controller. The controller owns planning,
commit/CI verification, evidence-based repair, and advancement.
"""
from __future__ import annotations

from scripts import apea_g_loop


def main() -> int:
    return apea_g_loop.main()


if __name__ == "__main__":
    raise SystemExit(main())
