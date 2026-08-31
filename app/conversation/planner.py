from typing import Dict, Optional


def plan_response_details(
    understanding: Dict,
    semantic: Optional[Dict] = None,
    state=None,
) -> Dict:
    """Return structured, internal response-planning evidence.

    Planning consumes conversation state and linguistic evidence without
    turning either into a replacement for the language model's reasoning.
    """
    semantic = semantic or {}
    intent = understanding.get("intent", "")
    dominant = semantic.get("dominant_signal", "statement")

    plans = {
        "clarification_request": "Clarify the immediately previous question or statement. Do not invent a new subject.",
        "agreement": "Acknowledge agreement naturally. Continue the current topic only if it has a natural next step.",
        "acknowledgement": "Treat the reply as context-dependent acknowledgement and react to the previous turn.",
        "continue_current_topic": "Continue or explain the current topic. Do not restart with a generic question.",
        "nothing_or_negative": "Accept the user's response naturally. Do not force an unrelated activity or topic.",
        "greeting": "Return a natural greeting appropriate to the current tone.",
    }
    instruction = plans.get(
        intent,
        "Respond directly to the user's meaning and context. Introduce a question only when conversationally useful.",
    )

    if dominant == "question":
        instruction += " The current utterance has question evidence; answer the question directly before adding anything else."
    elif dominant == "request":
        instruction += " The current utterance has request evidence; fulfill the requested action directly when possible."
    elif dominant == "negation":
        instruction += " The current utterance has negation evidence; preserve the user's negative constraint and do not infer an opposite request."

    return {
        "intent": intent,
        "confidence": understanding.get("confidence", "unknown"),
        "instruction": instruction,
        "dominant_signal": dominant,
        "topic": getattr(state, "topic", "") if state is not None else "",
        "open_question": getattr(state, "open_question", "") if state is not None else "",
        "has_previous_turn": bool(getattr(state, "recent", [])) if state is not None else False,
    }


def plan_response(understanding: Dict, semantic: Optional[Dict] = None, state=None) -> str:
    """Return the internal response instruction for existing callers."""
    return plan_response_details(understanding, semantic, state)["instruction"]
