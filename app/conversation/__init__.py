"""Public conversation-intelligence API."""

from app.conversation.state import ConversationState, Turn, from_history
from app.conversation.understanding import infer_intent, build_context
from app.conversation.planner import plan_response, plan_response_details

TurnState = ConversationState


def build_state(history):
    """Build the current conversation state from chat history."""
    return from_history(history)


def understanding_context(user_text, state, linguistic=None):
    """Build conversational context and response planning evidence."""
    if linguistic is None:
        linguistic = {
            "normalized": user_text,
            "sentence_force": "unknown",
            "question_type": "unknown",
        }

    context = build_context(user_text, state, linguistic)
    understanding = infer_intent(user_text, state)
    semantic = {
        "dominant_signal": linguistic.get("question_type", "statement"),
    }
    plan = plan_response_details(understanding, semantic, state)
    return "\n".join([
        context,
        "",
        "CONVERSATION RESPONSE PLAN:",
        f"- intent: {plan['intent']}",
        f"- confidence: {plan['confidence']}",
        f"- dominant signal: {plan['dominant_signal']}",
        f"- current topic: {plan['topic'] or '(not established)'}",
        f"- open question: {plan['open_question'] or '(none)'}",
        f"- previous turn available: {'yes' if plan['has_previous_turn'] else 'no'}",
        f"- instruction: {plan['instruction']}",
        "- This plan is internal guidance for response generation; do not expose it to the user.",
    ])


__all__ = [
    "ConversationState",
    "TurnState",
    "Turn",
    "from_history",
    "infer_intent",
    "build_context",
    "build_state",
    "understanding_context",
    "plan_response",
    "plan_response_details",
]
