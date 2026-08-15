
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache
from typing import Any

KINDS=("vocabulary","grammar","word_formation","syntax","examples","prose","rules","corpus","other")

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z][A-Za-z'-]*", (text or "").lower()))

def _stringify(value: Any) -> str:
    if isinstance(value, dict): return " ".join(f"{k} {_stringify(v)}" for k,v in value.items())
    if isinstance(value, list): return " ".join(_stringify(v) for v in value)
    return str(value or "")

@dataclass(frozen=True)
class SubjectDoc:
    path: str
    kind: str
    text: str
    entries: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    tokens: frozenset[str] = field(default_factory=frozenset)

@lru_cache(maxsize=1)
def build_index() -> tuple[SubjectDoc, ...]:
    docs=[]
    try:
        from app.database import language_documents
        for d in language_documents():
            text=str(d.get('text',''))
            docs.append(SubjectDoc(path=str(d.get('path','')),kind=str(d.get('kind','other')),text=text,entries=tuple(x for x in d.get('entries',[]) if isinstance(x,dict)),tokens=frozenset(_tokens(text))))
    except Exception:
        return tuple()
    return tuple(docs)


def reload_index() -> None:
    build_index.cache_clear()


def inventory() -> dict:
    docs = build_index()
    return {
        "documents": len(docs),
        "by_kind": {kind: sum(d.kind == kind for d in docs) for kind in KINDS},
        "entries": sum(len(d.entries) for d in docs),
        "paths": [d.path for d in docs],
    }


def _entry_score(query_tokens: set[str], entry: dict[str, Any], query: str) -> float:
    text = _stringify(entry)
    tokens = _tokens(text)
    overlap = len(query_tokens & tokens)
    score = overlap * 12

    low = text.lower()
    for t in query_tokens:
        if len(t) >= 2 and t in low:
            score += 1.5

    # Lexical mapping gets high priority when the user explicitly mentions
    # either side of a Standard/Melimi mapping.
    standard = str(entry.get("standard", "")).lower()
    melimi = str(entry.get("melimi", "")).lower()
    qlow = query.lower()
    if standard and standard in qlow:
        score += 60
    if melimi and melimi in qlow:
        score += 70
    return score


def retrieve(query: str, *, kinds: set[str] | None = None, limit: int = 14) -> list[dict]:
    qtokens = _tokens(query)
    if not qtokens:
        return []

    results = []
    for doc in build_index():
        if kinds and doc.kind not in kinds:
            continue

        # Document-level score.
        overlap = len(qtokens & set(doc.tokens))
        dscore = overlap * 3
        if dscore:
            results.append((dscore, doc, None))

        for entry in doc.entries:
            score = _entry_score(qtokens, entry, query)
            if score:
                results.append((score, doc, entry))

    results.sort(key=lambda x: (-x[0], x[1].path))
    out, seen = [], set()
    for score, doc, entry in results:
        key = (doc.path, json.dumps(entry, ensure_ascii=False, sort_keys=True) if entry else "")
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "score": round(score, 2),
            "source": doc.path,
            "kind": doc.kind,
            "entry": entry,
            "excerpt": "" if entry else re.sub(r"\s+", " ", doc.text)[:1800],
        })
        if len(out) >= limit:
            break
    return out


def _compact_docs(kind: str, max_chars: int) -> str:
    chunks = []
    for doc in build_index():
        if doc.kind != kind:
            continue
        text = re.sub(r"\n{3,}", "\n\n", doc.text).strip()
        if text:
            chunks.append(f"SOURCE {doc.path}:\n{text[:1800]}")
    return "\n\n".join(chunks)[:max_chars]


def language_profile(max_chars: int = 6500) -> str:
    """Stable subject profile: rules + representative language knowledge.

    It is cached locally and intentionally compact so every request does not
    send the entire corpus to Groq.
    """
    structured = []
    try:
        from app.database import language_rules, language_affixes
        for r in language_rules()[:20]:
            structured.append(f"RULE {r['name']}: {r['rule_text']} OPERATION={r['operation']}")
        for a in language_affixes()[:30]:
            structured.append(f"AFFIX {a['form']} ({a['kind']}) applies_to={a['applies_to']} meaning={a['meaning']}")
    except Exception:
        pass
    parts = [
        "MELIMI TELUGU — AUTHORITATIVE LANGUAGE SUBJECT",
        "The corpus is language knowledge, not a phrase bank.",
        "GRAMMAR/RULES STORED IN RUNTIME KNOWLEDGE:",
        "\n".join(structured),
        _compact_docs("rules", 1500),
        _compact_docs("grammar", 1500),
        _compact_docs("word_formation", 1500),
        _compact_docs("syntax", 700),
    ]
    return "\n\n".join(x for x in parts if x)[:max_chars]


def relevant_language_context(query: str, max_chars: int = 6500) -> str:
    # Structured JSON/Markdown retrieval remains primary. SQLite FTS5 adds broad
    # passage retrieval for the consolidated corpus and longer prose/grammar.
    results = retrieve(query, limit=16)
    # PostgreSQL/SQLAlchemy documents are the primary runtime retrieval store.
    # The legacy SQLite FTS helper is intentionally not required for production.
    fts_results = []

    if not results and not fts_results:
        return "No directly relevant subject item was retrieved. Do not invent Melimi facts."

    lines = ["RELEVANT MELIMI SUBJECT EVIDENCE:"]
    for item in results:
        lines.append(f"\n[{item['kind']}] {item['source']}")
        if item["entry"]:
            lines.append(json.dumps(item["entry"], ensure_ascii=False))
        elif item["excerpt"]:
            lines.append(item["excerpt"])

    seen = {(item["source"], item.get("excerpt", "")) for item in results}
    for item in fts_results:
        key = (item["source"], item["content"][:1800])
        if key in seen:
            continue
        lines.append(f"\n[corpus passage] {item['source']} / chunk {item['chunk_id']}")
        lines.append(item["content"])

    return "\n".join(lines)[:max_chars]
