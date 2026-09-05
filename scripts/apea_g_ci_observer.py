"""Commit-correlated GitHub Actions observer for APEA-G."""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "arjun939201/TeluAI")
API = "https://api.github.com"
POLL_SECONDS = 15
POLL_LIMIT = 80


def _token(for_dispatch: bool = False) -> str:
    if for_dispatch:
        value = os.environ.get("APEA_GITHUB_TOKEN")
        if not value:
            raise RuntimeError(
                "APEA_GITHUB_TOKEN is required to trigger GitHub Actions from APEA-G; "
                "GITHUB_TOKEN cannot safely be used as the workflow trigger credential"
            )
        return value
    value = os.environ.get("APEA_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not value:
        raise RuntimeError("A GitHub API token is required")
    return value


def _request(path: str, method: str = "GET", body=None, for_dispatch: bool = False):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{API}/repos/{REPO}/{path.lstrip('/')}",
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {_token(for_dispatch)}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TeluAI-APEA-G/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else {}


def dispatch_ci(branch: str) -> None:
    """Explicitly trigger CI with a non-GITHUB_TOKEN credential."""
    _request("actions/workflows/ci.yml/dispatches", "POST", {"ref": branch}, for_dispatch=True)


def current_head() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def wait_for_commit(branch: str, commit_sha: str | None = None, after: float | None = None):
    """Wait only for the CI run whose head SHA is the exact pushed commit."""
    target = commit_sha or current_head()
    for attempt in range(1, POLL_LIMIT + 1):
        query = (
            "actions/workflows/ci.yml/runs?branch="
            + urllib.parse.quote(branch, safe="")
            + "&per_page=50"
        )
        runs = _request(query).get("workflow_runs", [])
        matches = [r for r in runs if r.get("head_sha") == target]
        if after is not None:
            matches = [r for r in matches if r.get("created_at", "") >= time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(after - 10))]
        if matches:
            run = sorted(matches, key=lambda item: item.get("created_at", ""), reverse=True)[0]
            if run.get("status") == "completed":
                return run
        if attempt in (1, 4, 8):
            print(f"APEA-G waiting for CI: commit={target[:12]} attempt={attempt}/{POLL_LIMIT}")
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"CI did not complete for commit {target}")
