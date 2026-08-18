from __future__ import annotations

import json
from pathlib import Path

from app.chat.router import detect_language, route_message
from app.conversation.state import from_history
from app.conversation.understanding import infer_intent


CASES = Path(__file__).resolve().parents[1] / "evals" / "language_cases.json"


def run() -> dict:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    intent_total = intent_pass = language_total = language_pass = mode_total = mode_pass = 0
    failures = []
    state = from_history([])

    for case in cases:
        text = str(case.get("text", ""))
        if "expected_intent" in case:
            intent_total += 1
            actual = infer_intent(text, state).get("intent")
            if actual == case["expected_intent"]:
                intent_pass += 1
            else:
                failures.append({"id":case["id"],"metric":"intent","expected":case["expected_intent"],"actual":actual})
        if "expected_language" in case:
            language_total += 1
            actual = detect_language(text)
            if actual == case["expected_language"]:
                language_pass += 1
            else:
                failures.append({"id":case["id"],"metric":"language","expected":case["expected_language"],"actual":actual})
        if "expected_mode" in case:
            mode_total += 1
            actual = route_message(text, "auto").mode
            if actual == case["expected_mode"]:
                mode_pass += 1
            else:
                failures.append({"id":case["id"],"metric":"mode","expected":case["expected_mode"],"actual":actual})

    def pct(passed: int, total: int):
        return round(100.0 * passed / total, 2) if total else None

    return {
        "cases": len(cases),
        "intent_accuracy": pct(intent_pass, intent_total),
        "language_detection_accuracy": pct(language_pass, language_total),
        "mode_routing_accuracy": pct(mode_pass, mode_total),
        "failures": failures,
        "note": "Morphology/retrieval metrics are intentionally not fabricated here; they require a populated authoritative corpus and dedicated expected-behavior cases.",
    }


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
