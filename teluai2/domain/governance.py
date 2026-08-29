"""Governance rules for promoting AI discoveries into Melimi authority."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .language import AuthorityStatus, Candidate


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"


@dataclass(frozen=True)
class Review:
    reviewer_id: str
    decision: Decision
    expertise: str = "general"
    note: str = ""


@dataclass(frozen=True)
class GovernancePolicy:
    minimum_reviewers: int = 2
    minimum_acceptance_ratio: float = 0.67
    minimum_evidence_count: int = 1

    def evaluate(self, candidate: Candidate, reviews: Tuple[Review, ...]) -> AuthorityStatus:
        if len(candidate.evidence) < self.minimum_evidence_count:
            return AuthorityStatus.UNDER_REVIEW

        unique_reviewers = {review.reviewer_id for review in reviews if review.reviewer_id}
        if len(unique_reviewers) < self.minimum_reviewers:
            return AuthorityStatus.UNDER_REVIEW

        decisions = [review.decision for review in reviews]
        if Decision.INVESTIGATE in decisions:
            return AuthorityStatus.UNDER_REVIEW

        accepts = sum(decision is Decision.ACCEPT for decision in decisions)
        rejects = sum(decision is Decision.REJECT for decision in decisions)
        total = accepts + rejects
        if total == 0:
            return AuthorityStatus.UNDER_REVIEW
        if accepts / total >= self.minimum_acceptance_ratio:
            return AuthorityStatus.ACCEPTED
        if rejects / total > 0.5:
            return AuthorityStatus.REJECTED
        return AuthorityStatus.DISPUTED
