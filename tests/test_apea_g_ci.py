from scripts.apea_g_ci import FailureEvidence, FailureKind, classify_failure, classify_repeat


def evidence(logs, *, sha="abc", job="test", conclusion=None):
    return FailureEvidence(123, sha, job, ("pytest",), logs, conclusion)


def test_classifies_provider_failure():
    assert classify_failure(evidence("HTTP 403 from Groq API")) is FailureKind.PROVIDER


def test_classifies_dependency_failure():
    assert classify_failure(evidence("could not install dependency: no matching distribution")) is FailureKind.DEPENDENCY


def test_classifies_test_failure():
    assert classify_failure(evidence("pytest FAILED test_example")) is FailureKind.TEST


def test_classifies_infrastructure_failure():
    assert classify_failure(evidence("runner lost: job timed out")) is FailureKind.INFRASTRUCTURE


def test_detects_same_sha_with_conflicting_outcomes_as_flaky():
    previous = evidence("pytest assertion A", conclusion="failure")
    current = evidence("pytest assertion A", conclusion="success")
    assert classify_repeat(previous, current) is FailureKind.FLAKY


def test_same_sha_repeated_failure_is_not_flaky():
    previous = evidence("pytest assertion A", conclusion="failure")
    current = evidence("pytest assertion A", conclusion="failure")
    assert classify_repeat(previous, current) is None


def test_does_not_call_different_sha_flaky():
    previous = evidence("pytest assertion A", sha="old", conclusion="failure")
    current = evidence("pytest assertion A", sha="new", conclusion="success")
    assert classify_repeat(previous, current) is None
