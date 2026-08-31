"""Public conversation-intelligence API."""

from app.conversation.state import ConversationState, Turn, from_history
from app.conversation.understanding import infer_intent, build_context

TurnState = ConversationState


def build_state(history):
    """Build the current conversation state from chat history."""
    return from_history(history)


def understanding_context(user_text, state, linguistic=None):
    """Build conversational context from conversation state and real language analysis."""
    if linguistic is None:
        linguistic = {
            "normalized": user_text,
            "sentence_force": "unknown",
            "question_type": "unknown",
        }
    return build_context(user_text, state, linguistic)


__all__ = [
    "ConversationState",
    "TurnState",
    "Turn",
    "from_history",
    "infer_intent",
    "build_context",
    "build_state",
    "understanding_context",
]
