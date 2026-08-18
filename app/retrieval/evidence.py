from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import re
from typing import Any, Iterable


class Authority(IntEnum):
    UNKNOWN = 0
    MODEL_KNOWLEDGE = 10
    PROPOSED = 30
    APPROVED = 50
    VERIFIED = 70
    MASTER = 100


_STATUS_AUTHORITY = {
    "MASTER": Authority.MASTER,
    "VERIFIED": Authority.VERIFIED,
    "APPROVED": Authority.APPROVED,
    "PROPOSED": Authority.PROPOSED,
    "PENDING": Authority.PROPOSED,
}


@dataclass(frozen=True)
class KnowledgeEvidence:
    source: str
    status: str
    authority: Authority
    confidence: float
    version: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    lexical_score: float = 0.0
    relevance_score: float = 0.0

    @property
    def authoritative(self) -> bool:
        return self.authority >= Authority.MASTER


@dataclass(frozen=True)
class EvidenceSet:
    items: tuple[KnowledgeEvidence, ...]
    knowledge_version: int
    sufficient: bool

    @property
    def insufficient(self) -> bool:
        return not self.sufficient


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z]+", (text or "").casefold()))


def _authority(status: str, source: str) -> Authority:
    status_value = str(status or "").upper().strip()
    if status_value in _STATUS_AUTHORITY:
        return _STATUS_AUTHORITY[status_value]
    if str(source or "").startswith("model:"):
        return Authority.MODEL_KNOWLEDGE
    return Authority.UNKNOWN


def _lexical_score(query: str, payload: dict[str, Any]) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    searchable = " ".join(str(v) for v in payload.values() if isinstance(v, (str, int, float)))
    tokens = _tokens(searchable)
    overlap = len(query_tokens & tokens)
    standard = str(payload.get("standard", "")).casefold()
    melimi = str(payload.get("melimi", "")).casefold()
    query_value = (query or "").casefold()
    score = overlap * 8.0
    if standard and standard in query_value:
        score += 60.0
    if melimi and melimi in query_value:
        score += 70.0
    return score


def rank_evidence(entries: Iterable[dict[str, Any]], query: str, knowledge_version: int, limit: int = 16) -> EvidenceSet:
    ranked: list[KnowledgeEvidence] = []
    for entry in entries:
        payload = dict(entry.get("entry") or entry)
        source = str(entry.get("source") or payload.get("source") or "unknown")
        status = str(entry.get("status") or payload.get("status") or "UNKNOWN").upper()
        version = int(entry.get("version") or payload.get("version") or knowledge_version or 0)
        authority = _authority(status, source)
        lexical = _lexical_score(query, payload)
        if lexical <= 0:
            continue
        confidence = max(0.0, min(1.0, (authority / 100.0) * 0.75 + min(lexical / 100.0, 0.25)))
        ranked.append(KnowledgeEvidence(
            source=source,
            status=status,
            authority=authority,
            confidence=confidence,
            version=version,
            kind=str(entry.get("kind") or payload.get("kind") or "other"),
            payload=payload,
            lexical_score=lexical,
            relevance_score=authority * 2.0 + lexical,
        ))

    ranked.sort(key=lambda item: (-item.relevance_score, -item.lexical_score, item.source))
    ranked = ranked[: max(1, min(limit, 50))]
    sufficient = any(item.authoritative and item.lexical_score > 0 for item in ranked)
    return EvidenceSet(tuple(ranked), int(knowledge_version or 0), sufficient)


def format_evidence(evidence: EvidenceSet, max_chars: int = 5000) -> str:
    if evidence.insufficient:
        return "INSUFFICIENT_LANGUAGE_EVIDENCE: no authoritative language evidence was retrieved. Do not invent a Melimi fact."
    lines = [
        f"LANGUAGE EVIDENCE (knowledge_version={evidence.knowledge_version}):",
        "Authority order: MASTER > VERIFIED > APPROVED > PROPOSED > MODEL_KNOWLEDGE > UNKNOWN.",
    ]
    for item in evidence.items:
        payload = item.payload
        standard = str(payload.get("standard", "")).strip()
        melimi = str(payload.get("melimi", "")).strip()
        if standard or melimi:
            description = f"{standard} → {melimi}"
        else:
            description = str(payload.get("content") or payload.get("value") or "").strip()
        lines.append(
            f"- [{item.status}] authority={int(item.authority)} confidence={item.confidence:.2f} "
            f"source={item.source} version={item.version}: {description}"
        )
        if len("\n".join(lines)) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]
