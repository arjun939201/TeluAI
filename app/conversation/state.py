from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class ConversationState:
    """Small, derived state used to understand the next user turn.

    It is deliberately separate from raw chat history. The state describes
    what is currently open in the conversation rather than merely repeating
    previous messages.
    """
    topic: Optional[str] = None
    last_user_intent: Optional[str] = None
    last_assistant_intent: Optional[str] = None
    open_question: Optional[str] = None
    pending_reference: Optional[str] = None
    tone: str = "casual"
    recent_turns: List[ConversationTurn] = field(default_factory=list)

    def add_turn(self, role: str, content: str, limit: int = 8) -> None:
        self.recent_turns.append(ConversationTurn(role, content))
        self.recent_turns = self.recent_turns[-limit:]

    def context_text(self) -> str:
        lines = [
            "CONVERSATION STATE:",
            f"- topic: {self.topic or 'not established'}",
            f"- last user intent: {self.last_user_intent or 'unknown'}",
            f"- last assistant intent: {self.last_assistant_intent or 'unknown'}",
            f"- open question: {self.open_question or 'none'}",
            f"- pending reference: {self.pending_reference or 'none'}",
            f"- tone: {self.tone}",
        ]
        return "\n".join(lines)


def infer_open_question(assistant_text: str) -> Optional[str]:
    """Conservative local detection of an unanswered question.

    This is not a full parser. It supplies a useful hint without another
    LLM/API request.
    """
    text = (assistant_text or "").strip()
    if not text:
        return None

    question_mark = "?" in text or "？" in text
    if not question_mark:
        return None

    return text
