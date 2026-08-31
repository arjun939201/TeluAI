"""Public conversation-intelligence API."""

from app.conversation.state import ConversationState, Turn, from_history
from app.conversation.understanding import infer_intent, build_context
from app.conversation.planner import plan_response

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
    plan = plan_response(understanding, semantic)
    return "\n".join([
        context,
        "",
        "CONVERSATION RESPONSE PLAN:",
        f"- {plan}",
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
]
