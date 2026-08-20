from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.chat.router import detect_language, route_message
from app.conversation.state import from_history
from app.conversation.understanding import infer_intent
from app.melimi.root_morphology import convert_surface
from app.retrieval.evidence import rank_evidence


CASES = Path(__file__).resolve().parents[1] / "evals" / "language_cases.json"


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


def run() -> dict[str, Any]:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    intent_total = intent_pass = language_total = language_pass = mode_total = mode_pass = 0
    morphology_total = morphology_pass = unsupported_total = unsupported_pass = 0
    authority_total = authority_pass = 0
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
            actual = detect_language(text)
            if actual == case["expected_language"]:
                language_pass += 1
            else:
                failures.append({"id": case_id, "metric": "language", "expected": case["expected_language"], "actual": actual})
        if "expected_mode" in case:
            mode_total += 1
            actual = route_message(text, "auto").mode
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

    return {
        "cases": len(cases),
        "intent_accuracy": _pct(intent_pass, intent_total),
        "language_detection_accuracy": _pct(language_pass, language_total),
        "mode_routing_accuracy": _pct(mode_pass, mode_total),
        "melimi_morphology_accuracy": _pct(morphology_pass, morphology_total),
        "unsupported_rejection_accuracy": _pct(unsupported_pass, unsupported_total),
        "authority_adherence": _pct(authority_pass, authority_total),
        "retrieval_precision": None,
        "retrieval_recall": None,
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
        },
        "note": "Metrics without deterministic offline ground truth are reported as null, never fabricated. LLM quality, latency and token metrics require a provider-backed evaluation run.",
    }


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
