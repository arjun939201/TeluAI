from typing import Dict, Optional


def _topic_relation_from_context(state) -> str:
    """Read the latest conversation relation without inventing a new topic."""
    if state is None:
        return "unknown"
    topic = getattr(state, "topic", "")
    return "established" if topic else "new"


def plan_response_details(
    understanding: Dict,
    semantic: Optional[Dict] = None,
    state=None,
) -> Dict:
    """Return structured, internal response-planning evidence.

    Planning consumes conversation state and linguistic evidence without
    replacing the language model's reasoning.  It explicitly separates the
    current conversational move from the established topic.
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

    relation = semantic.get("topic_relation", "")
    if relation == "possible_topic_shift":
        instruction += " A possible topic shift is detected; answer the current utterance, while retaining prior context as background until the shift is clear."
    elif relation == "continuation":
        instruction += " Treat the established topic as active unless the current utterance clearly overrides it."

    if semantic.get("reference_detected"):
        instruction += " A conversational reference is present; resolve it against reliable prior semantic context before answering."

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
        "topic_relation": relation or _topic_relation_from_context(state),
        "open_question": getattr(state, "open_question", "") if state is not None else "",
        "has_previous_turn": bool(getattr(state, "recent", [])) if state is not None else False,
        "reference_detected": bool(semantic.get("reference_detected", False)),
    }


def plan_response(understanding: Dict, semantic: Optional[Dict] = None, state=None) -> str:
    """Return the internal response instruction for existing callers."""
    return plan_response_details(understanding, semantic, state)["instruction"]
