from scripts.apea_g_ci import FailureEvidence, FailureKind, classify_failure, classify_failure_action, classify_repeat, evidence_record, failure_signature, repair_confidence


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


def test_classifies_contract_mismatch_before_generic_test_failure():
    logs = "AssertionError: expected_evidence_ids: knowledge/1:word; actual_evidence_ids: language_space:knowledge/1:word"
    assert classify_failure(evidence(logs)) is FailureKind.CONTRACT


def test_classifies_fixture_mismatch():
    assert classify_failure(evidence("evaluation corpus fixture is missing expected_evidence_ids")) is FailureKind.FIXTURE


def test_extracts_contract_values_and_records_them_without_logs():
    logs = "expected_evidence_ids: knowledge/1:word\nactual_evidence_ids: language_space:knowledge/1:word"
    record = evidence_record(evidence(logs))
    assert record["contract_mismatch"] == {"expected": "knowledge/1:word", "actual": "language_space:knowledge/1:word"}
    assert "logs" not in record
    assert record["confidence"] == "high"


def test_failure_signature_is_stable_and_secret_free():
    first = evidence("HTTP 403 secret_token 123456789")
    second = evidence("HTTP 403 secret_token 987654321")
    assert failure_signature(first) == failure_signature(second)
    assert "123456789" not in failure_signature(first)


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


def test_maps_failures_to_bounded_recovery_actions():
    assert classify_failure_action(FailureKind.TEST) == "repair"
    assert classify_failure_action(FailureKind.CONTRACT) == "repair_contract"
    assert classify_failure_action(FailureKind.FIXTURE) == "repair_fixture"
    assert classify_failure_action(FailureKind.PROVIDER) == "wait_provider"
    assert classify_failure_action(FailureKind.INFRASTRUCTURE) == "retry_ci"
    assert classify_failure_action(FailureKind.FLAKY) == "retry_ci"
    assert classify_failure_action(FailureKind.UNKNOWN) == "diagnose"


def test_confidence_gate_is_conservative():
    assert repair_confidence(FailureKind.CONTRACT, evidence("x")) == "high"
    assert repair_confidence(FailureKind.REGRESSION, evidence("x")) == "medium"
    assert repair_confidence(FailureKind.UNKNOWN, evidence("x")) == "low"
