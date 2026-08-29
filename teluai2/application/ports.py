"""Dependency-inversion ports for the TeluAI 2 application layer."""
from __future__ import annotations

from typing import Protocol, Sequence

from teluai2.domain.language import Candidate, Lexeme, LookupResult


class Lexicon(Protocol):
    def lookup(self, query: str) -> LookupResult: ...
    def authoritative(self) -> Sequence[Lexeme]: ...


class CandidateRepository(Protocol):
    def save(self, candidate: Candidate) -> Candidate: ...


class DiscoveryAI(Protocol):
    def analyze(self, text: str) -> Candidate | None: ...
