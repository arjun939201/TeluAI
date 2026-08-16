"""Conversation intelligence exports and backwards-compatible names."""

from app.conversation.state import ConversationState, Turn, from_history
from app.conversation.understanding import infer_intent, build_context

# Older tests/integrations used TurnState. Keep the public alias while the
# implementation uses the clearer ConversationState name.
TurnState = ConversationState

__all__ = ["ConversationState", "TurnState", "Turn", "from_history", "infer_intent", "build_context"]
