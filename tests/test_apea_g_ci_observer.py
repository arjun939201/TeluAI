from __future__ import annotations

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


def test_dispatch_prefers_dedicated_token(monkeypatch):
    captured = {}

    def fake_request(path, method="GET", body=None, for_dispatch=False):
        captured.update(path=path, method=method, body=body, for_dispatch=for_dispatch)
        return {}

    monkeypatch.setenv("APEA_GITHUB_TOKEN", "dedicated")
    monkeypatch.setenv("GITHUB_TOKEN", "default")
    monkeypatch.setattr(observer, "_request", fake_request)

    observer.dispatch_ci("apea-g/continuous-boot")

    assert captured["for_dispatch"] is True
    assert captured["body"] == {"ref": "apea-g/continuous-boot"}


def test_dispatch_falls_back_to_github_token(monkeypatch):
    captured = {}

    def fake_request(path, method="GET", body=None, for_dispatch=False):
        captured["for_dispatch"] = for_dispatch
        return {}

    monkeypatch.delenv("APEA_GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "default")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(observer, "_request", fake_request)

    observer.dispatch_ci("apea-g/continuous-boot")

    assert captured["for_dispatch"] is True
