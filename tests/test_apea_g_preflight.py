from scripts.apea_g_preflight import preflight, patch_paths


def test_extracts_changed_paths():
    patch = "diff --git a/app/example.py b/app/example.py\n--- a/app/example.py\n+++ b/app/example.py\n@@ -1 +1 @@\n-old\n+new\n"
    assert patch_paths(patch) == ("app/example.py",)


def test_maps_language_change_to_affected_tests():
    patch = "--- a/app/retrieval/evidence.py\n+++ b/app/retrieval/evidence.py\n@@ -1 +1 @@\n-a\n+b\n"
    report = preflight(patch)
    assert report.ok
    assert "language" in report.affected_areas
    assert "tests/test_eval_contract.py" in report.affected_tests


def test_blocks_apea_control_paths():
    patch = "--- a/scripts/apea_g.py\n+++ b/scripts/apea_g.py\n@@ -1 +1 @@\n-a\n+b\n"
    report = preflight(patch)
    assert not report.ok
    assert report.risk == "blocked"


def test_blocks_empty_patch():
    report = preflight("")
    assert not report.ok
    assert "empty patch" in report.violations


def test_multiple_areas_raise_risk():
    patch = "--- a/app/account_service.py\n+++ b/app/account_service.py\n@@ -1 +1 @@\n-a\n+b\n--- a/render.yaml\n+++ b/render.yaml\n@@ -1 +1 @@\n-a\n+b\n"
    report = preflight(patch)
    assert report.risk == "high"
