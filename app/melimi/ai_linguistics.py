"""AI-assisted Melimi linguistics engine with deterministic morphology routing.

The AI supplies general linguistic reasoning and candidate analyses/derivations,
while the Melimi roots and grammar policy remain authoritative.

The routing layer deliberately runs BEFORE/AROUND AI reasoning:
- exact matching: authoritative root -> authoritative Melimi root
- front-routing: surface form -> root -> Melimi root -> same operations -> target surface
- back-routing: root -> planned operations -> target surface
- chain matching: root -> plural -> oblique/adjectival/case/etc.
- provenance: every generated form records its route and evidence
AI output remains advisory and is never promoted to MASTER automatically.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from app.config import settings
from app.melimi.db_subject import language_roots
from app.melimi.grammar import grammar_policy


def _compact_roots(limit: int = 160) -> str:
    roots = language_roots()
    items = list(roots.items())[:limit]
    return "\n".join(f"- {src} -> {mt}" for src, mt in items)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _suffix_chain(value: str) -> list[dict[str, str]]:
    """Conservative Telugu surface clues used for deterministic routing.

    These are routing hints, not a replacement for the authoritative grammar.
    The AI/grammar policy can accept, reject, or refine the candidate chain.
    """
    value = _normalize(value)
    chain: list[dict[str, str]] = []
    if value.endswith("లు") and len(value) > 2:
        chain.append({"operation": "plural", "surface": value})
        value = value[:-2]
    # A plural oblique/adjectival form commonly ends in ల; keep the plural
    # operation explicit so root -> plural -> oblique is routable as one chain.
    if value.endswith("ాల") and len(value) > 3:
        chain.append({"operation": "plural_oblique", "surface": value})
    elif value.endswith("ల") and len(value) > 2:
        chain.append({"operation": "oblique", "surface": value})
    return chain


def _find_root_for_surface(surface: str, roots: dict[str, str]) -> tuple[str, str, list[dict[str, str]]]:
    value = _normalize(surface)
    # Exact source/root match wins.
    if value in roots:
        return value, roots[value], [{"operation": "identity", "surface": value}]

    # Deterministic front-routing: peel only known surface patterns, then
    # match the resulting lexical root. Never invent a root from an arbitrary
    # Telugu word.
    candidates: list[tuple[str, str, list[dict[str, str]]]] = []
    for source, mt in roots.items():
        if value == source:
            candidates.append((source, mt, [{"operation": "identity", "surface": value}]))
            continue
        if value.startswith(source):
            tail = value[len(source):]
            if tail:
                candidates.append((source, mt, [{"operation": "suffix", "value": tail, "surface": value}]))

    # Handle the common noun chain explicitly: root -> plural -> plural-oblique.
    for source, mt in roots.items():
        if value == source + "లు":
            candidates.append((source, mt, [{"operation": "plural", "surface": value}]))
        if value == source + "ల":
            candidates.append((source, mt, [{"operation": "oblique", "surface": value}]))
        if value == source + "ాలు":
            candidates.append((source, mt, [{"operation": "plural", "surface": source + "లు"}, {"operation": "plural_oblique", "surface": value}]))

    if not candidates:
        # Limited suffix stripping only; this remains a candidate and is later
        # validated by the grammar/AI layer.
        for suffix, operation in (("లు", "plural"), ("ల", "oblique"), ("ాలు", "plural_oblique")):
            if value.endswith(suffix) and len(value) > len(suffix) + 1:
                stem = value[:-len(suffix)]
                if stem in roots:
                    candidates.append((stem, roots[stem], [{"operation": operation, "surface": value}]))

    if not candidates:
        return "", "", []
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    return candidates[0]


def _apply_operation(source: str, operation: str, value: str = "") -> str:
    """Apply only operations with deterministic safe surface behavior."""
    if operation == "identity":
        return source
    if operation == "plural":
        # Telugu noun plural is not universally productive in one shape; this
        # is a planned candidate, not an automatic MASTER assertion.
        if source.endswith("ం"):
            return source[:-1] + "ాలు"
        return source + "లు"
    if operation == "plural_oblique":
        plural = _apply_operation(source, "plural")
        if plural.endswith("లు"):
            return plural[:-2] + "ల"
        return plural + "ల"
    if operation == "oblique":
        if source.endswith("లు"):
            return source[:-2] + "ల"
        return source + "ల"
    if operation == "suffix":
        return source + value
    return source


def plan_chain(word_or_phrase: str, task: str = "Analyze morphology and route source/root to Melimi.") -> dict[str, Any]:
    """Build a deterministic front/back/matching chain before AI reasoning."""
    value = _normalize(word_or_phrase)
    roots = language_roots()
    root, melimi_root, front_ops = _find_root_for_surface(value, roots)
    if not root:
        return {
            "status": "UNSUPPORTED",
            "route": "front-routing",
            "input": value,
            "root": "",
            "melimi_root": "",
            "operations": [],
            "chain": [],
            "matches": [],
        }

    chain = [{"stage": "source_root", "form": root, "operation": "root"},
             {"stage": "melimi_root", "form": melimi_root, "operation": "lexical_mapping"}]
    target = melimi_root
    back_ops: list[dict[str, str]] = []
    for op in front_ops:
        operation = op.get("operation", "")
        if operation == "identity":
            continue
        generated = _apply_operation(target, operation, op.get("value", ""))
        back_ops.append({"operation": operation, "source_surface": op.get("surface", ""), "target_surface": generated})
        chain.append({"stage": "derived", "form": generated, "operation": operation})
        target = generated

    return {
        "status": "MASTER" if root in roots else "SUPPORTED_CANDIDATE",
        "route": "front-routing→back-routing",
        "input": value,
        "root": root,
        "melimi_root": melimi_root,
        "operations": front_ops,
        "back_operations": back_ops,
        "chain": chain,
        "surface_match": target == value,
        "matches": [{"source": root, "melimi": melimi_root, "confidence": 1.0}],
        "notes": "Deterministic chain is a routing candidate; grammar policy/AI may validate or refine it.",
    }


def _prompt(word_or_phrase: str, task: str, planned_chain: dict[str, Any]) -> str:
    return f"""You are the linguistic analysis engine for Melimi Telugu, a Telugu-based constructed/native vocabulary system.

AUTHORITATIVE DATA HAS PRIORITY:
1. Supplied Melimi roots/mappings are authoritative.
2. Supplied Melimi grammar policy is authoritative.
3. General linguistic knowledge may reason about morphology, inflection, derivation, agreement, allomorphy, POS, tense/aspect/mood, case, number, person, and productive word formation.
4. Never invent an existing Melimi lexical root. If a needed root is absent, mark it UNSUPPORTED.
5. Generated derivatives/inflections are candidates unless explicitly verified as MASTER.
6. Preserve lexical identity and transfer the SAME grammatical operations from source/root to Melimi root.
7. Do not treat an arbitrary Telugu word as Melimi merely because it is Telugu.
8. Use the planned deterministic chain below as the first hypothesis. Correct it only when the supplied grammar/corpus gives evidence.

PLANNED ROUTING CHAIN:
{json.dumps(planned_chain, ensure_ascii=False, indent=2)}

MELIMI GRAMMAR POLICY:
{grammar_policy()}

AUTHORITATIVE ROOTS:
{_compact_roots()}

TASK: {task}
INPUT: {word_or_phrase}

Return compact JSON only with keys:
analysis, root, melimi_root, part_of_speech, operations, generated_forms, confidence, status, route, matches, notes

generated_forms must contain form, function, evidence, and route for each form.
status: MASTER, SUPPORTED_CANDIDATE, UNSUPPORTED, or NEEDS_REVIEW.
"""


def analyze(word_or_phrase: str, task: str = "Analyze morphology and generate supported inflections/derivatives.") -> dict[str, Any]:
    value = _normalize(word_or_phrase)
    planned = plan_chain(value, task)
    if not settings.groq_token:
        planned.update({"status": "NEEDS_REVIEW", "analysis": "GROQ_API_KEY is not configured."})
        return planned

    payload = {
        "model": settings.groq_model,
        "temperature": 0.1,
        "max_tokens": 1600,
        "messages": [
            {"role": "system", "content": "You are a precise computational linguist. Output JSON only."},
            {"role": "user", "content": _prompt(value, task, planned)},
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
        result.setdefault("route", planned.get("route"))
        result.setdefault("matches", planned.get("matches", []))
        result.setdefault("planned_chain", planned.get("chain", []))
        return result
    except Exception as exc:
        planned.update({"status": "NEEDS_REVIEW", "analysis": "AI linguistic analysis failed.", "notes": str(exc)[:300]})
        return planned


def format_for_agent(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)[:9000]
