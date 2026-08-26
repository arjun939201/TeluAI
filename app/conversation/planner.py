from typing import Dict, Optional


def plan_response(understanding: Dict, semantic: Optional[Dict] = None) -> str:
    intent = understanding.get("intent", "")
    semantic = semantic or {}

    plans = {
        "clarification_request": "Clarify the immediately previous question or statement. Do not invent a new subject.",
        "agreement": "Acknowledge agreement naturally. Continue the current topic only if it has a natural next step.",
        "acknowledgement": "Treat the reply as context-dependent acknowledgement and react to the previous turn.",
        "continue_current_topic": "Continue or explain the current topic. Do not restart with a generic question.",
        "nothing_or_negative": "Accept the user's response naturally. Do not force an unrelated activity or topic.",
        "greeting": "Return a natural greeting appropriate to the current tone.",
    }
    plan = plans.get(
        intent,
        "Respond directly to the user's meaning and context. Introduce a question only when conversationally useful.",
    )

    # Semantic signals are evidence for response planning, never replacement commands.
    dominant = semantic.get("dominant_signal", "statement")
    if dominant == "question":
        plan += " The current utterance has question evidence; answer the question directly before adding anything else."
    elif dominant == "request":
        plan += " The current utterance has request evidence; fulfill the requested action directly when possible."
    elif dominant == "negation":
        plan += " The current utterance has negation evidence; preserve the user's negative constraint and do not infer an opposite request."
    return plan
