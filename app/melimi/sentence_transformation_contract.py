"""Public contract for sentence-level Melimi transformation results."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TransformationIssue:
    token: str
    reason: str


@dataclass(frozen=True)
class SentenceTransformation:
    source: str
    transformed: str
    changed_tokens: int
    unresolved_tokens: Tuple[str, ...] = ()
    issues: Tuple[TransformationIssue, ...] = ()

    @property
    def safe(self) -> bool:
        return not self.issues
