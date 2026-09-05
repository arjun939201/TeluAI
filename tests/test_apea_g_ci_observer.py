from __future__ import annotations

import pytest

from scripts import apea_g_ci_observer as observer


def test_wait_for_commit_correlates_exact_head_sha(monkeypatch):
    calls = []
    target = "target-sha"

    def fake_request(path, method="GET", body=None, for_dispatch=False):
        calls.append(path)
        return {
            "workflow_runs": [
                {"id": 1, "head_sha": "other-sha", "status": "completed", "conclusion": "success", "created_at": "2026-09-05T06:00:00Z"},
                {"id": 2, "head_sha": target, "status": "in_progress", "conclusion": None, "created_at": "2026-09-05T06:01:00Z"},
                {"id": 3, "head_sha": target, "status": "completed", "conclusion": "success", "created_at": "2026-09-05T06:02:00Z"},
            ]
        }

    monkeypatch.setattr(observer, "_request", fake_request)
    monkeypatch.setattr(observer.time, "sleep", lambda _: None)

    run = observer.wait_for_commit("apea-g/continuous-boot", target)

    assert run["id"] == 3
    assert len(calls) == 1


def test_dispatch_requires_dedicated_automation_token(monkeypatch):
    monkeypatch.delenv("APEA_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="APEA_GITHUB_TOKEN is required"):
        observer.dispatch_ci("apea-g/continuous-boot")
