"""AI-assisted Melimi linguistics engine.

The AI supplies general linguistic reasoning and candidate analyses/derivations,
while the PostgreSQL Melimi roots and grammar policy remain authoritative.
AI output is advisory: it is never promoted to MASTER automatically.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from app.config import settings
from app.melimi.db_subject import language_roots
from app.melimi.grammar import grammar_policy


def _compact_roots(limit: int = 120) -> str:
    roots = language_roots()
    items = list(roots.items())[:limit]
    return "\n".join(f"- {src} -> {mt}" for src, mt in items)


def _prompt(word_or_phrase: str, task: str) -> str:
    return f"""You are the linguistic analysis engine for Melimi Telugu, a Telugu-based constructed/native vocabulary system.

AUTHORITATIVE DATA HAS PRIORITY:
1. The supplied Melimi roots/mappings are authoritative.
2. The supplied Melimi grammar policy is authoritative.
3. General linguistic knowledge may be used to reason about morphology, inflection, derivation, agreement, sandhi/allomorphy, POS, tense/aspect/mood, case, number, person, and productive word formation.
4. Never invent an existing Melimi lexical root. If a needed root is absent, mark it as UNSUPPORTED instead of silently inventing one.
5. You may GENERATE a candidate derivative/inflection from an authoritative root when the grammar policy supports it. Clearly label generated forms as CANDIDATE, not MASTER.
6. Preserve the distinction between lexical identity and surface inflection. For example, an old surface form must be mapped through its source/root and then the latest Melimi root must receive the same grammatical operations.
7. Do not treat an arbitrary Telugu word as Melimi merely because it is Telugu.

MELIMI GRAMMAR POLICY:
{grammar_policy()}

AUTHORITATIVE ROOTS (sample/current database):
{_compact_roots()}

TASK: {task}
INPUT: {word_or_phrase}

Return compact JSON only with these keys:
analysis, root, melimi_root, part_of_speech, operations, generated_forms, confidence, status, notes

- operations: ordered morphology/grammar operations with their function.
- generated_forms: list of objects with form, function, and evidence (RULE or AI_GENERAL_KNOWLEDGE).
- status must be one of MASTER, SUPPORTED_CANDIDATE, UNSUPPORTED, NEEDS_REVIEW.
- If the input is an inflection, identify the lexical root and reconstruct the equivalent Melimi inflection from the Melimi root.
- If the input asks for derivatives, generate only forms licensed by the supplied grammar policy and root category.
"""


def analyze(word_or_phrase: str, task: str = "Analyze morphology and generate supported inflections/derivatives.") -> dict[str, Any]:
    if not settings.groq_token:
        return {"status": "NEEDS_REVIEW", "analysis": "GROQ_API_KEY is not configured."}
    payload = {
        "model": settings.groq_model,
        "temperature": 0.1,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You are a precise computational linguist. Output JSON only."},
            {"role": "user", "content": _prompt(str(word_or_phrase).strip(), task)},
        ],
    }
    request = urllib.request.Request(
        settings.groq_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.groq_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = str(body["choices"][0]["message"]["content"]).strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("AI result is not an object")
        return result
    except Exception as exc:
        return {"status": "NEEDS_REVIEW", "analysis": "AI linguistic analysis failed.", "notes": str(exc)[:300]}


def format_for_agent(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)[:7000]
