from scripts.apea_g_ci import FailureEvidence, FailureKind, classify_failure, classify_repeat


def evidence(logs, *, sha="abc", job="test"):
    return FailureEvidence(123, sha, job, ("pytest",), logs)


def test_classifies_provider_failure():
    assert classify_failure(evidence("HTTP 403 from Groq API")) is FailureKind.PROVIDER


def test_classifies_dependency_failure():
    assert classify_failure(evidence("could not install dependency: no matching distribution")) is FailureKind.DEPENDENCY


def test_classifies_test_failure():
    assert classify_failure(evidence("pytest FAILED test_example")) is FailureKind.TEST


def test_classifies_infrastructure_failure():
    assert classify_failure(evidence("runner lost: job timed out")) is FailureKind.INFRASTRUCTURE


def test_detects_repeated_same_sha_with_changed_evidence_as_flaky():
    previous = evidence("pytest FAILED assertion A")
    current = evidence("pytest FAILED assertion B")
    assert classify_repeat(previous, current) is FailureKind.FLAKY


def test_does_not_call_different_sha_flaky():
    previous = evidence("pytest FAILED assertion A", sha="old")
    current = evidence("pytest FAILED assertion B", sha="new")
    assert classify_repeat(previous, current) is None
