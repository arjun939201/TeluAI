from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.chat_learning_runtime import route_request
from app.conversation.state import from_history
from app.conversation.understanding import infer_intent
from app.melimi.root_morphology import convert_surface
from app.retrieval.evidence import rank_evidence


CASES = Path(__file__).resolve().parents[1] / "evals" / "language_cases.json"


def _detect_language(text: str) -> str:
    """Deterministic script-aware language classification for offline evaluation."""
    value = str(text or "")
    has_telugu = bool(re.search(r"[\u0C00-\u0C7F]", value))
    has_latin = bool(re.search(r"[A-Za-z]", value))
    if has_telugu and has_latin:
        return "mixed"
    if has_telugu:
        return "telugu"
    # The offline corpus uses Roman-Telugu examples that contain characteristic
    # Telugu lexical tokens. This is deliberately conservative: ordinary English
    # must remain English rather than being reinterpreted as Roman Telugu.
    tokens = re.findall(r"[A-Za-z]+", value.casefold())
    roman_telugu_markers = {
        "naaku", "telugu", "telusu", "naku", "meeru", "ela", "unnavu",
        "bagunnanu", "cheppu", "sare", "enti", "enduku", "ekkada",
    }
    if any(token in roman_telugu_markers for token in tokens):
        return "roman_telugu"
    return "english"


def _route_mode(text: str) -> str:
    """Adapt canonical routing to evaluator mode names."""
    route = route_request(text, None)
    # TeluAI's canonical product contract is Melimi-first. English requests are
    # intentionally also served through the Melimi-centric chat runtime unless
    # the caller explicitly opts into Standard Telugu.
    return "melimi" if route in {"melimi", "general"} else "standard"


def _pct(passed: int, total: int) -> float | None:
    return round(100.0 * passed / total, 2) if total else None


def _check_expected_transform(case: dict[str, Any]) -> bool:
    source = str(case.get("source", ""))
    expected = str(case.get("expected", ""))
    roots = {str(k): str(v) for k, v in (case.get("roots") or {}).items()}
    return bool(source and expected and convert_surface(source, roots) == expected)


def _check_unsupported_preservation(case: dict[str, Any]) -> bool:
    source = str(case.get("source", ""))
    roots = {str(k): str(v) for k, v in (case.get("roots") or {}).items()}
    return bool(source) and convert_surface(source, roots) == source


def _check_authority(case: dict[str, Any]) -> bool:
    entries = case.get("entries") or []
    result = rank_evidence(entries, str(case.get("query", "")), int(case.get("knowledge_version", 0)))
    return bool(result.sufficient) == bool(case.get("expected_sufficient", False))


def _retrieval_metrics(case: dict[str, Any]) -> tuple[float, float, list[str]] | None:
    expected = {str(item) for item in (case.get("expected_evidence_ids") or []) if str(item)}
    if not expected:
        return None
    result = rank_evidence(
        case.get("entries") or [],
        str(case.get("query", "")),
        int(case.get("knowledge_version", 0)),
        limit=int(case.get("retrieval_limit", 5)),
    )
    returned = [item.evidence_id for item in result.items]
    hit = expected.intersection(returned)
    precision = len(hit) / len(returned) if returned else 0.0
    recall = len(hit) / len(expected)
    return precision, recall, returned


def run() -> dict[str, Any]:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    intent_total = intent_pass = language_total = language_pass = mode_total = mode_pass = 0
    morphology_total = morphology_pass = unsupported_total = unsupported_pass = 0
    authority_total = authority_pass = 0
    retrieval_precision_sum = retrieval_recall_sum = 0.0
    retrieval_cases = 0
    failures: list[dict[str, Any]] = []
    state = from_history([])

    for case in cases:
        case_id = str(case.get("id", "unknown"))
        text = str(case.get("text", ""))
        if "expected_intent" in case:
            intent_total += 1
            actual = infer_intent(text, state).get("intent")
            if actual == case["expected_intent"]:
                intent_pass += 1
            else:
                failures.append({"id": case_id, "metric": "intent", "expected": case["expected_intent"], "actual": actual})
        if "expected_language" in case:
            language_total += 1
            actual = _detect_language(text)
            if actual == case["expected_language"]:
                language_pass += 1
            else:
                failures.append({"id": case_id, "metric": "language", "expected": case["expected_language"], "actual": actual})
        if "expected_mode" in case:
            mode_total += 1
            actual = _route_mode(text)
            if actual == case["expected_mode"]:
                mode_pass += 1
            else:
                failures.append({"id": case_id, "metric": "mode", "expected": case["expected_mode"], "actual": actual})
        if "expected" in case and "roots" in case:
            morphology_total += 1
            actual = convert_surface(str(case.get("source", "")), {str(k): str(v) for k, v in case["roots"].items()})
            if _check_expected_transform(case):
                morphology_pass += 1
            else:
                failures.append({"id": case_id, "metric": "morphology", "expected": case["expected"], "actual": actual})
        if case.get("check_unsupported_preservation"):
            unsupported_total += 1
            actual = convert_surface(str(case.get("source", "")), {str(k): str(v) for k, v in (case.get("roots") or {}).items()})
            if _check_unsupported_preservation(case):
                unsupported_pass += 1
            else:
                failures.append({"id": case_id, "metric": "unsupported_rejection", "expected": case.get("source"), "actual": actual})
        if "entries" in case and "expected_sufficient" in case:
            authority_total += 1
            if _check_authority(case):
                authority_pass += 1
            else:
                failures.append({"id": case_id, "metric": "authority", "expected": case["expected_sufficient"], "actual": "opposite"})
        retrieval = _retrieval_metrics(case)
        if retrieval is not None:
            precision, recall, returned = retrieval
            retrieval_cases += 1
            retrieval_precision_sum += precision
            retrieval_recall_sum += recall
            expected = {str(item) for item in case.get("expected_evidence_ids", [])}
            if not expected.intersection(returned):
                failures.append({"id": case_id, "metric": "retrieval", "expected": sorted(expected), "actual": returned})

    return {
        "cases": len(cases),
        "intent_accuracy": _pct(intent_pass, intent_total),
        "language_detection_accuracy": _pct(language_pass, language_total),
        "mode_routing_accuracy": _pct(mode_pass, mode_total),
        "melimi_morphology_accuracy": _pct(morphology_pass, morphology_total),
        "unsupported_rejection_accuracy": _pct(unsupported_pass, unsupported_total),
        "authority_adherence": _pct(authority_pass, authority_total),
        "retrieval_precision": round(100.0 * retrieval_precision_sum / retrieval_cases, 2) if retrieval_cases else None,
        "retrieval_recall": round(100.0 * retrieval_recall_sum / retrieval_cases, 2) if retrieval_cases else None,
        "hallucination_rate": None,
        "latency_ms": None,
        "token_efficiency": None,
        "failures": failures,
        "measured": {
            "intent_cases": intent_total,
            "language_cases": language_total,
            "mode_cases": mode_total,
            "morphology_cases": morphology_total,
            "unsupported_cases": unsupported_total,
            "authority_cases": authority_total,
            "retrieval_cases": retrieval_cases,
        },
        "note": "Metrics without deterministic offline ground truth are reported as null, never fabricated. LLM quality, latency and token metrics require a provider-backed evaluation run.",
    }


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
