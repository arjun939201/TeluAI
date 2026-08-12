import re
from typing import Dict, Optional

from .state import ConversationState


SHORT_INPUTS = {
    "enti": {"clarification", "question"},
    "emiti": {"clarification", "question"},
    "em": {"clarification", "question"},
    "haa": {"acknowledgement"},
    "haaa": {"acknowledgement"},
    "sare": {"agreement"},
    "okay": {"agreement"},
    "ok": {"agreement"},
    "avunu": {"agreement"},
    "cheppu": {"request_to_continue"},
    "inka": {"request_to_continue"},
    "emledhu": {"negative_or_nothing"},
    "em ledu": {"negative_or_nothing"},
    "nothing": {"negative_or_nothing"},
}


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def understand_user_turn(
    user_text: str,
    state: ConversationState,
) -> Dict[str, object]:
    """Interpret the current turn relative to the current conversation.

    Critical rule: short/ambiguous inputs are interpreted with the previous
    assistant turn and open question, not as isolated dictionary entries.
    """
    raw = user_text.strip()
    key = _normalized(raw)

    candidates = SHORT_INPUTS.get(key, set())
    previous = state.recent_turns[-1].content if state.recent_turns else ""

    if key in {"enti", "emiti", "em"}:
        if state.open_question or previous:
            return {
                "meaning": "The user is asking for clarification about the previous message/question.",
                "intent": "clarification_request",
                "confidence": "high",
                "candidates": sorted(candidates),
            }
        return {
            "meaning": "The user is asking 'what?' or asking for clarification.",
            "intent": "question",
            "confidence": "medium",
            "candidates": sorted(candidates),
        }

    if key in {"haa", "haaa"}:
        return {
            "meaning": "The user is acknowledging/agreeing with the previous turn; exact force depends on context.",
            "intent": "acknowledgement",
            "confidence": "medium",
            "candidates": sorted(candidates),
        }

    if key == "sare":
        return {
            "meaning": "The user is accepting or agreeing with the previous turn.",
            "intent": "agreement",
            "confidence": "medium",
            "candidates": sorted(candidates),
        }

    if key in {"cheppu", "inka"}:
        return {
            "meaning": "The user wants the assistant to continue, tell more, or explain further.",
            "intent": "continue_request",
            "confidence": "medium",
            "candidates": sorted(candidates),
        }

    return {
        "meaning": "Interpret the message from the complete conversation, not from isolated word lookup.",
        "intent": "contextual_understanding",
        "confidence": "unknown",
        "candidates": sorted(candidates),
    }


def build_understanding_context(
    user_text: str,
    state: ConversationState,
) -> str:
    result = understand_user_turn(user_text, state)

    return "\n".join([
        "CONTEXTUAL USER UNDERSTANDING:",
        f"- user input: {user_text.strip()}",
        f"- interpreted meaning: {result['meaning']}",
        f"- intent: {result['intent']}",
        f"- confidence: {result['confidence']}",
        "- IMPORTANT: do not treat a short reply as an independent new topic when it naturally responds to the previous turn.",
        "- Answer the user's actual conversational move before introducing a new topic.",
    ])
