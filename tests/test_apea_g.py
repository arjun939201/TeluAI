import subprocess

import pytest

from scripts.apea_g import apply_patch, ci_failure_context, parse_json


def test_parse_json_accepts_plain_and_fenced_json():
    assert parse_json('{"action":"audit"}') == {"action": "audit"}
    assert parse_json('```json\n{"action":"repair"}\n```') == {"action": "repair"}


def test_parse_json_rejects_non_object():
    with pytest.raises((ValueError, TypeError)):
        parse_json("not json")


def test_apply_patch_rejects_secret_paths():
    patch = "--- /dev/null\n+++ b/.env\n@@ -0,0 +1 @@\n+SECRET=x\n"
    with pytest.raises(ValueError):
        apply_patch(patch)


def test_apply_patch_rejects_agent_control_paths():
    for path in (".github/workflows/apea-g.yml", "scripts/apea_g.py"):
        patch = f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+disabled: true\n"
        with pytest.raises(ValueError):
            apply_patch(patch)


def test_ci_failure_context_preserves_run_metadata_without_api_call():
    context = ci_failure_context({"workflow_run": {"id": 123, "conclusion": "success", "head_sha": "abc"}})
    assert context["run_id"] == 123
    assert context["conclusion"] == "success"
    assert context["head_sha"] == "abc"


def test_agent_module_has_no_uncommitted_changes_after_import():
    result = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, check=True)
    assert "scripts/apea_g.py" not in result.stdout
