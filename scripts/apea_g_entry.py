"""Autonomous APEA-G entrypoint with resilient provider and PR fallbacks."""
from __future__ import annotations
import time
import urllib.error

from scripts import apea_g_full as full
from scripts import apea_g_loop as core

_ORIGINAL_ENSURE_PR = core.ensure_pr
_ORIGINAL_PROVIDER = full.provider
MAX_PROVIDER_RETRIES = 4


def safe_ensure_pr(branch: str):
    """Do not let a repository policy blocking PR creation halt engineering."""
    try:
        return _ORIGINAL_ENSURE_PR(branch)
    except urllib.error.HTTPError as exc:
        if exc.code != 403:
            raise
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            pass
        print(f"APEA-G PR creation unavailable (HTTP 403); continuing without PR: {detail}")
        return None


def resilient_provider(instruction: str):
    """Retry transient Groq rate limits without treating them as product failures."""
    for attempt in range(1, MAX_PROVIDER_RETRIES + 1):
        try:
            return _ORIGINAL_PROVIDER(instruction)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= MAX_PROVIDER_RETRIES:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = max(2, min(60, int(float(retry_after)))) if retry_after else min(30, 2 ** attempt)
            except (TypeError, ValueError):
                delay = min(30, 2 ** attempt)
            print(f"APEA-G provider rate-limited; retry {attempt + 1}/{MAX_PROVIDER_RETRIES} after {delay}s")
            time.sleep(delay)


core.ensure_pr = safe_ensure_pr
full.provider = resilient_provider

if __name__ == "__main__":
    raise SystemExit(full.main())
