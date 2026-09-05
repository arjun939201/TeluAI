from scripts.apea_g_preflight import affected_subsystems, focused_tests, run


def ownership():
    return {
        "schema_version": 1,
        "protected_paths": [".github/workflows/apea-g.yml", "scripts/apea_g_loop.py"],
        "high_risk_subsystems": ["authentication"],
        "subsystems": [
            {"id": "authentication", "paths": ["app/account_service.py"], "tests": ["tests/test_auth.py"]},
            {"id": "evaluation", "paths": ["evals/**"], "tests": ["tests/test_eval_contract.py"]},
        ],
    }


def test_maps_changed_paths_to_subsystems():
    data = ownership()
    files = ("app/account_service.py", "evals/language_cases.json")
    assert affected_subsystems(files, data) == ("authentication", "evaluation")


def test_maps_changes_to_focused_tests_without_duplicates():
    data = ownership()
    files = ("app/account_service.py", "app/account_service.py")
    assert focused_tests(files, data) == ("tests/test_auth.py",)


def test_protected_path_change_fails_closed():
    result = run(("scripts/apea_g_loop.py",),)
    assert result.ok is False
    assert result.risk == "high"
    assert "scripts/apea_g_loop.py" in result.errors[0]


def test_ordinary_change_is_low_risk_when_contract_is_valid():
    result = run(("evals/language_cases.json",),)
    assert result.ok is True
    assert result.risk == "low"
    assert "evaluation" in result.affected_subsystems
    assert "tests/test_eval_contract.py" in result.focused_tests


def test_large_change_set_is_medium_risk():
    files = tuple(f"docs/file-{index}.md" for index in range(9))
    result = run(files)
    assert result.ok is True
    assert result.risk == "medium"
