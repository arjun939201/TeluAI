"""Pure Melimi language domain primitives.

No FastAPI, SQLAlchemy, provider SDK, or browser concerns belong here.  This
module defines the vocabulary/grammar contract that every application surface
will consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple


class AuthorityStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"
    DEPRECATED = "DEPRECATED"


class EvidenceType(str, Enum):
    HISTORICAL_TEXT = "HISTORICAL_TEXT"
    DICTIONARY = "DICTIONARY"
    INSCRIPTION = "INSCRIPTION"
    RURAL_USAGE = "RURAL_USAGE"
    ORAL_RECORD = "ORAL_RECORD"
    ONLINE_SOURCE = "ONLINE_SOURCE"
    LINGUISTIC_ANALYSIS = "LINGUISTIC_ANALYSIS"
    MELIMI_CORPUS = "MELIMI_CORPUS"


@dataclass(frozen=True)
class Evidence:
    source_id: str
    evidence_type: EvidenceType
    citation: str
    excerpt: str = ""
    reliability: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.citation.strip():
            raise ValueError("citation is required")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between 0 and 1")


@dataclass(frozen=True)
class Lexeme:
    id: str
    form: str
    meaning: str
    category: str
    status: AuthorityStatus
    root_id: str | None = None
    variants: Tuple[str, ...] = ()
    evidence: Tuple[Evidence, ...] = ()
    version: int = 1
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.form.strip():
            raise ValueError("lexeme id and form are required")
        if self.version < 1:
            raise ValueError("version must be positive")

    @property
    def is_authoritative(self) -> bool:
        return self.status is AuthorityStatus.ACCEPTED


@dataclass(frozen=True)
class MorphologyRule:
    id: str
    name: str
    category: str
    description: str
    operation: str
    status: AuthorityStatus = AuthorityStatus.ACCEPTED
    evidence: Tuple[Evidence, ...] = ()

    @property
    def is_authoritative(self) -> bool:
        return self.status is AuthorityStatus.ACCEPTED


@dataclass(frozen=True)
class LookupResult:
    query: str
    matches: Tuple[Lexeme, ...]
    authoritative: bool
    reason: str


@dataclass(frozen=True)
class Candidate:
    id: str
    proposed_form: str
    meaning: str
    rationale: str
    evidence: Tuple[Evidence, ...] = ()
    ai_confidence: float | None = None
    status: AuthorityStatus = AuthorityStatus.CANDIDATE
    reviewer_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.ai_confidence is not None and not 0 <= self.ai_confidence <= 1:
            raise ValueError("ai_confidence must be between 0 and 1")

    @property
    def can_be_runtime_authority(self) -> bool:
        return self.status is AuthorityStatus.ACCEPTED
