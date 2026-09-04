"""Deterministic CI evidence collection, classification, and repair guidance for APEA-G."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re


class FailureKind(str, Enum):
    TEST = "test"
    CONTRACT = "contract_mismatch"
    FIXTURE = "fixture_mismatch"
    REGRESSION = "product_regression"
    BUILD = "build"
    DEPENDENCY = "dependency"
    WORKFLOW = "workflow"
    PROVIDER = "provider"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    REPAIR = "repair"
    REPAIR_CONTRACT = "repair_contract"
    REPAIR_FIXTURE = "repair_fixture"
    REPAIR_PRODUCT = "repair_product"
    REPAIR_WORKFLOW = "repair_workflow"
    WAIT_PROVIDER = "wait_provider"
    RETRY_CI = "retry_ci"
    DIAGNOSE = "diagnose"


@dataclass(frozen=True)
class FailureEvidence:
    workflow_run_id: int | None
    head_sha: str | None
    job_name: str | None
    failed_steps: tuple[str, ...]
    logs: str
    conclusion: str | None = None


def _text(evidence: FailureEvidence) -> str:
    return f"{evidence.job_name or ''} {' '.join(evidence.failed_steps)} {evidence.logs}".lower()


def failure_signature(evidence: FailureEvidence) -> str:
    """Stable, secret-free signature used to remember recurring failures."""
    normalized = re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", _text(evidence))
    normalized = re.sub(r"\b\d+\b", "<n>", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def extract_contract_mismatch(logs: str) -> dict[str, str] | None:
    """Extract common expected/actual assertion values without depending on pytest formatting."""
    text = logs
    expected = re.search(r"expected(?:_evidence_ids?)?[^\n]*?[:=]\s*['\"]?([^'\"\n]+)", text, re.I)
    actual = re.search(r"actual(?:_evidence_ids?)?[^\n]*?[:=]\s*['\"]?([^'\"\n]+)", text, re.I)
    if expected and actual:
        return {"expected": expected.group(1).strip(), "actual": actual.group(1).strip()}
    return None


def classify_failure(evidence: FailureEvidence) -> FailureKind:
    text = _text(evidence)
    mismatch = extract_contract_mismatch(evidence.logs)
    if mismatch:
        return FailureKind.CONTRACT
    if any(x in text for x in ("fixture", "golden data", "expected_evidence_ids", "evaluation corpus")):
        return FailureKind.FIXTURE
    if any(x in text for x in ("groq", "openai_api_key", "api key", "401", "403", "429", "provider unavailable")):
        return FailureKind.PROVIDER
    if any(x in text for x in ("timeout", "timed out", "runner lost", "no space left", "rate limit")):
        return FailureKind.INFRASTRUCTURE
    if any(x in text for x in ("dependency", "could not install", "no matching distribution", "resolution impossible")):
        return FailureKind.DEPENDENCY
    if any(x in text for x in ("yaml", "workflow", "action.yml", "github actions")):
        return FailureKind.WORKFLOW
    if any(x in text for x in ("compile", "syntaxerror", "importerror", "build failed")):
        return FailureKind.BUILD
    if any(x in text for x in ("assert", "failed", "failure", "pytest", "test_")):
        return FailureKind.TEST
    return FailureKind.UNKNOWN


def classify_repeat(previous: FailureEvidence | None, current: FailureEvidence) -> FailureKind | None:
    """Return FLAKY only when the same SHA/job/failed steps have conflicting outcomes."""
    if not previous or previous.head_sha != current.head_sha:
        return None
    if previous.job_name != current.job_name or previous.failed_steps != current.failed_steps:
        return None
    if {previous.conclusion, current.conclusion} != {"success", "failure"}:
        return None
    return FailureKind.FLAKY


def classify_failure_action(kind: FailureKind) -> str:
    """Map evidence class to a bounded controller action."""
    return {
        FailureKind.TEST: RecoveryAction.REPAIR.value,
        FailureKind.CONTRACT: RecoveryAction.REPAIR_CONTRACT.value,
        FailureKind.FIXTURE: RecoveryAction.REPAIR_FIXTURE.value,
        FailureKind.REGRESSION: RecoveryAction.REPAIR_PRODUCT.value,
        FailureKind.BUILD: RecoveryAction.REPAIR.value,
        FailureKind.DEPENDENCY: RecoveryAction.REPAIR.value,
        FailureKind.WORKFLOW: RecoveryAction.REPAIR_WORKFLOW.value,
        FailureKind.PROVIDER: RecoveryAction.WAIT_PROVIDER.value,
        FailureKind.INFRASTRUCTURE: RecoveryAction.RETRY_CI.value,
        FailureKind.FLAKY: RecoveryAction.RETRY_CI.value,
        FailureKind.UNKNOWN: RecoveryAction.DIAGNOSE.value,
    }[kind]


def repair_confidence(kind: FailureKind, evidence: FailureEvidence) -> str:
    """Conservative confidence gate for autonomous repair selection."""
    if kind in {FailureKind.CONTRACT, FailureKind.FIXTURE, FailureKind.BUILD, FailureKind.DEPENDENCY}:
        return "high"
    if kind in {FailureKind.TEST, FailureKind.WORKFLOW, FailureKind.REGRESSION}:
        return "medium"
    return "low"


def evidence_record(evidence: FailureEvidence) -> dict[str, object]:
    """Produce a durable, non-secret failure record for APEA-G state/history."""
    kind = classify_failure(evidence)
    return {
        "workflow_run_id": evidence.workflow_run_id,
        "head_sha": evidence.head_sha,
        "job_name": evidence.job_name,
        "failed_steps": list(evidence.failed_steps),
        "conclusion": evidence.conclusion,
        "kind": kind.value,
        "action": classify_failure_action(kind),
        "confidence": repair_confidence(kind, evidence),
        "signature": failure_signature(evidence),
        "contract_mismatch": extract_contract_mismatch(evidence.logs),
    }
