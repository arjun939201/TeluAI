"""Autonomous APEA-G entrypoint with resilient provider and CI/PR fallbacks."""
from __future__ import annotations
import os
import time
import urllib.error

from scripts import apea_g_ci_observer as ci_observer
from scripts import apea_g_full as full
from scripts import apea_g_loop as core

_ORIGINAL_ENSURE_PR = core.ensure_pr
_ORIGINAL_PROVIDER = full.provider
_ORIGINAL_TOKEN = core.token
_ORIGINAL_INSTALL_GUARDS = full.install_runtime_guards
MAX_PROVIDER_RETRIES = 4


def api_token() -> str:
    """Prefer the dedicated automation credential for write/API lifecycle operations."""
    return os.environ.get("APEA_GITHUB_TOKEN") or _ORIGINAL_TOKEN()


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


def dispatch_ci(branch: str):
    """Trigger CI explicitly with the available workflow-dispatch credential."""
    return ci_observer.dispatch_ci(branch)


def wait_ci(branch: str, after: float):
    """Correlate CI to the exact commit produced by the current step."""
    import subprocess

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ci_observer.ROOT, text=True).strip()
    run = ci_observer.wait_for_commit(branch, head, after)
    print(f"APEA-G CI observed: commit={head[:12]} run={run.get('id')} conclusion={run.get('conclusion')}")
    return run


def install_runtime_guards():
    """Install full-run guards without replacing the CI observer lifecycle hooks."""
    _ORIGINAL_INSTALL_GUARDS()
    core.dispatch_ci = dispatch_ci
    core.wait_ci = wait_ci
    core.ensure_pr = safe_ensure_pr
    core.token = api_token


core.token = api_token
core.ensure_pr = safe_ensure_pr
core.dispatch_ci = dispatch_ci
core.wait_ci = wait_ci
full.provider = resilient_provider
full.install_runtime_guards = install_runtime_guards

if __name__ == "__main__":
    raise SystemExit(full.main())
