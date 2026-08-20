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
    """One traceable piece of language evidence.

    The evidence object deliberately keeps authority separate from confidence:
    a model can be highly confident about a guess, but that guess is still not
    language authority until it is published in Language Space.
    """

    source: str
    status: str
    authority: Authority
    confidence: float
    version: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_id: str = ""
    source_type: str = ""
    provenance: str = ""
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    grammatical_score: float = 0.0
    contextual_score: float = 0.0
    freshness_score: float = 1.0
    relevance_score: float = 0.0

    @property
    def authoritative(self) -> bool:
        return self.authority is Authority.MASTER

    @property
    def evidence_id(self) -> str:
        return self.source_id or f"{self.source_type}:{self.source}"


@dataclass(frozen=True)
class EvidenceSet:
    items: tuple[KnowledgeEvidence, ...]
    knowledge_version: int
    sufficient: bool
    reason: str = ""

    @property
    def insufficient(self) -> bool:
        return not self.sufficient

    @property
    def authoritative_items(self) -> tuple[KnowledgeEvidence, ...]:
        return tuple(item for item in self.items if item.authoritative)

    def explain(self) -> list[dict[str, Any]]:
        return [
            {
                "evidence_id": item.evidence_id,
                "source": item.source,
                "source_type": item.source_type,
                "status": item.status,
                "authority": item.authority.name,
                "confidence": round(item.confidence, 4),
                "version": item.version,
                "provenance": item.provenance,
                "scores": {
                    "lexical": round(item.lexical_score, 4),
                    "semantic": round(item.semantic_score, 4),
                    "grammatical": round(item.grammatical_score, 4),
                    "contextual": round(item.contextual_score, 4),
                    "freshness": round(item.freshness_score, 4),
                    "relevance": round(item.relevance_score, 4),
                },
            }
            for item in self.items
        ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z]+", (text or "").casefold()))


def _authority(status: str, source: str) -> Authority:
    status_value = str(status or "").upper().strip()
    if status_value in _STATUS_AUTHORITY:
        return _STATUS_AUTHORITY[status_value]
    if str(source or "").startswith("model:"):
        return Authority.MODEL_KNOWLEDGE
    return Authority.UNKNOWN


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


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


def rank_evidence(
    entries: Iterable[dict[str, Any]],
    query: str,
    knowledge_version: int,
    limit: int = 16,
) -> EvidenceSet:
    """Rank retrieved records without allowing weak evidence to become authority."""
    ranked: list[KnowledgeEvidence] = []
    current_version = int(knowledge_version or 0)

    for entry in entries:
        payload = dict(entry.get("entry") or entry)
        source = str(entry.get("source") or payload.get("source") or "unknown")
        status = str(entry.get("status") or payload.get("status") or "UNKNOWN").upper()
        version = int(entry.get("version") or payload.get("version") or current_version or 0)
        authority = _authority(status, source)
        lexical = _lexical_score(query, payload)
        if lexical <= 0:
            continue

        semantic = _bounded(payload.get("semantic_score", payload.get("semantic_match", 0.0)))
        grammatical = _bounded(payload.get("grammatical_score", payload.get("grammatical_match", 0.0)))
        contextual = _bounded(payload.get("contextual_score", payload.get("contextual_match", 0.0)))
        freshness = 1.0 if version == current_version else max(0.0, 1.0 - min(abs(current_version - version), 10) / 10)
        authority_factor = authority / 100.0
        confidence = max(
            0.0,
            min(
                1.0,
                authority_factor * 0.65
                + min(lexical / 100.0, 0.20)
                + semantic * 0.05
                + grammatical * 0.05
                + contextual * 0.05,
            ),
        )
        relevance = (
            authority * 2.0
            + lexical
            + semantic * 20.0
            + grammatical * 15.0
            + contextual * 15.0
            + freshness * 5.0
        )
        ranked.append(
            KnowledgeEvidence(
                source=source,
                status=status,
                authority=authority,
                confidence=confidence,
                version=version,
                kind=str(entry.get("kind") or payload.get("kind") or "other"),
                payload=payload,
                source_id=str(entry.get("source_id") or payload.get("id") or ""),
                source_type=str(entry.get("source_type") or payload.get("source_type") or "language_space"),
                provenance=str(entry.get("provenance") or payload.get("provenance") or source),
                lexical_score=lexical,
                semantic_score=semantic,
                grammatical_score=grammatical,
                contextual_score=contextual,
                freshness_score=freshness,
                relevance_score=relevance,
            )
        )

    ranked.sort(key=lambda item: (-item.authority, -item.relevance_score, -item.lexical_score, item.source))
    ranked = ranked[: max(1, min(limit, 50))]
    sufficient = any(item.authoritative and item.lexical_score > 0 for item in ranked)
    reason = "authoritative evidence retrieved" if sufficient else "no published MASTER evidence satisfies the query"
    return EvidenceSet(tuple(ranked), current_version, sufficient, reason)


def format_evidence(evidence: EvidenceSet, max_chars: int = 5000) -> str:
    if evidence.insufficient:
        return (
            "INSUFFICIENT_LANGUAGE_EVIDENCE: no authoritative language evidence was retrieved. "
            "Do not invent a Melimi fact."
        )
    lines = [
        f"LANGUAGE EVIDENCE (knowledge_version={evidence.knowledge_version}):",
        "Authority order: MASTER > VERIFIED > APPROVED > PROPOSED > MODEL_KNOWLEDGE > UNKNOWN.",
        f"Evidence state: {evidence.reason}.",
    ]
    for item in evidence.items:
        payload = item.payload
        standard = str(payload.get("standard", "")).strip()
        melimi = str(payload.get("melimi", "")).strip()
        description = f"{standard} → {melimi}" if (standard or melimi) else str(payload.get("content") or payload.get("value") or "").strip()
        lines.append(
            f"- [{item.status}] authority={item.authority.name} confidence={item.confidence:.2f} "
            f"source={item.source} version={item.version}: {description}"
        )
        if len("\n".join(lines)) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]
