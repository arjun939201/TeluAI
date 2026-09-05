import json

import pytest

from scripts import apea_g_runner


def test_resilient_provider_retries_malformed_json(monkeypatch):
    calls = []

    def provider(_instruction):
        calls.append(1)
        if len(calls) < 2:
            raise json.JSONDecodeError("bad", "{", 1)
        return {"action": "implement"}

    monkeypatch.setattr(apea_g_runner.apea_g_loop, "provider", provider)
    assert apea_g_runner.resilient_provider("x") == {"action": "implement"}
    assert len(calls) == 2


def test_resilient_provider_is_bounded(monkeypatch):
    def provider(_instruction):
        raise json.JSONDecodeError("bad", "{", 1)

    monkeypatch.setattr(apea_g_runner.apea_g_loop, "provider", provider)
    with pytest.raises(RuntimeError, match="bounded retries"):
        apea_g_runner.resilient_provider("x")
