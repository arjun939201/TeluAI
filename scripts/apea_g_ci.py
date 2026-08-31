"""Deterministic CI evidence collection and failure classification for APEA-G."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureKind(str, Enum):
    TEST = "test"
    BUILD = "build"
    DEPENDENCY = "dependency"
    WORKFLOW = "workflow"
    PROVIDER = "provider"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureEvidence:
    workflow_run_id: int | None
    head_sha: str | None
    job_name: str | None
    failed_steps: tuple[str, ...]
    logs: str
    conclusion: str | None = None


def classify_failure(evidence: FailureEvidence) -> FailureKind:
    text = f"{evidence.job_name or ''} {' '.join(evidence.failed_steps)} {evidence.logs}".lower()
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
        FailureKind.TEST: "repair",
        FailureKind.BUILD: "repair",
        FailureKind.DEPENDENCY: "repair",
        FailureKind.WORKFLOW: "repair_workflow",
        FailureKind.PROVIDER: "wait_provider",
        FailureKind.INFRASTRUCTURE: "retry_ci",
        FailureKind.FLAKY: "retry_ci",
        FailureKind.UNKNOWN: "diagnose",
    }[kind]
