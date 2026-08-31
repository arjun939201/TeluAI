from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import re

from app.conversation.semantic import SemanticFact, facts_from_representation, merge_facts, semantic_context


@dataclass
class Turn:
    role: str
    content: str


@dataclass
class ConversationState:
    topic: str = ""
    open_question: str = ""
    last_user_intent: str = ""
    last_assistant_intent: str = ""
    tone: str = "casual"
    recent: List[Turn] = field(default_factory=list)
    semantic_facts: Tuple[SemanticFact, ...] = field(default_factory=tuple)

    def add(self, role: str, content: str, limit: int = 10):
        self.recent.append(Turn(role, content))
        self.recent = self.recent[-limit:]

    def add_semantic_facts(self, facts: List[SemanticFact] | Tuple[SemanticFact, ...]) -> None:
        self.semantic_facts = merge_facts(self.semantic_facts, facts)

    @property
    def last_assistant(self) -> str:
        for turn in reversed(self.recent):
            if turn.role == "assistant":
                return turn.content
        return ""

    @property
    def last_user(self) -> str:
        for turn in reversed(self.recent):
            if turn.role == "user":
                return turn.content
        return ""

    @property
    def last_substantive_user(self) -> str:
        """Return the latest user turn that can establish a topic anchor."""
        short = {"hi", "hello", "hey", "haa", "haaa", "sare", "ok", "okay", "avunu", "cheppu", "inka", "enti", "emiti", "emle", "emledu", "emledhu", "ఏంటి", "ఏమిటి", "ఏం", "ఏమి", "సరే", "అవును", "చెప్పు", "ఇంకా", "ఏంలేదు"}
        for turn in reversed(self.recent):
            if turn.role != "user":
                continue
            text = re.sub(r"\s+", " ", turn.content.strip())
            if len(text) > 12 and text.casefold() not in short:
                return text
        return ""

    def context_text(self) -> str:
        semantic = semantic_context(self.semantic_facts)
        return "\n".join([
            "CONVERSATION STATE:",
            f"- topic: {self.topic or '(not established)'}",
            f"- open question: {self.open_question or '(none)'}",
            f"- last user intent: {self.last_user_intent or '(unknown)'}",
            f"- tone: {self.tone}",
            f"- semantic facts: {semantic['facts']}",
        ])


def from_history(history: List[Dict]) -> ConversationState:
    state = ConversationState()
    for item in (history or [])[-10:]:
        if not isinstance(item, dict):
            continue
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            state.add(item["role"], item["content"].strip())

    # Reconstruct semantic memory from prior user turns through TEX-L's
    # evidence-first representation. Invalid enrichment never breaks chat.
    from app.texl_representation import representation_context
    for turn in state.recent:
        if turn.role != "user":
            continue
        try:
            representation = representation_context(turn.content)
            state.add_semantic_facts(facts_from_representation(representation))
        except Exception:
            continue

    state.topic = state.last_substantive_user

    assistant = state.last_assistant
    if assistant and (
        "?" in assistant or "？" in assistant
        or any(x in assistant for x in ("ఏంటి", "ఏమి", "ఎలా", "ఎందుకు", "ఎక్కడ", "ఎప్పుడు"))
    ):
        state.open_question = assistant
    return state
