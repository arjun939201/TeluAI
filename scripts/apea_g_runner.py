"""APEA-G autonomous entrypoint with bounded provider-output recovery."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import apea_g_loop  # noqa: E402


MAX_PROVIDER_RETRIES = 2


def resilient_provider(instruction: str):
    """Retry transient malformed model JSON without changing engineering policy."""
    last_error = None
    for _ in range(MAX_PROVIDER_RETRIES + 1):
        try:
            return apea_g_loop.provider(instruction)
        except json.JSONDecodeError as exc:
            last_error = exc
    raise RuntimeError("LLM returned malformed JSON after bounded retries") from last_error


def main() -> int:
    apea_g_loop.provider = resilient_provider
    return apea_g_loop.main()


if __name__ == "__main__":
    raise SystemExit(main())
