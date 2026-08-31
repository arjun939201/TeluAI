"""Conversation-aware response instructions."""
from __future__ import annotations

from typing import Any


def _response_strategy(plan: dict[str, Any]) -> tuple[str, str, str]:
    """Select a compact response strategy from validated conversation planning."""
    intent = str(plan.get("intent") or "").strip()
    if intent == "clarification_request":
        return "clarify", "high", "resolve the immediately referenced prior context before answering"
    if intent == "agreement":
        return "acknowledge", "medium", "acknowledge naturally and continue only when a next step is useful"
    if intent == "acknowledgement":
        return "acknowledge", "medium", "respond to the acknowledgement in context without restarting the conversation"
    if intent == "continue_current_topic":
        return "continue", "high", "continue the established topic and answer the current move first"
    if intent == "nothing_or_negative":
        return "respect_constraint", "high", "preserve the user's negative or stopping constraint without forcing a new task"
    if intent == "greeting":
        return "greet", "low", "return a natural greeting in the requested language and tone"
    if plan.get("reference_detected"):
        return "resolve_reference", "high", "resolve the conversational reference against reliable prior context"
    if plan.get("dominant_signal") == "question":
        return "answer", "high", "answer the current question directly before optional explanation"
    if plan.get("dominant_signal") == "request":
        return "fulfill", "high", "fulfill the current request directly when possible"
    if plan.get("dominant_signal") == "negation":
        return "respect_constraint", "high", "preserve the user's negative constraint"
    return "direct", "medium", "respond directly to the user's meaning and context"


def build_response_context(plan: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    """Build concise internal guidance for natural, context-aware responses."""
    context = context or {}
    strategy, priority, action = _response_strategy(plan)
    lines = [
        "CONVERSATIONAL RESPONSE GUIDANCE:",
        f"- current intent: {plan.get('intent', 'unknown')}",
        f"- topic relation: {plan.get('topic_relation', 'unknown')}",
        f"- established topic: {plan.get('topic') or '(none)'}",
        f"- open question: {plan.get('open_question') or '(none)'}",
        f"- reference detected: {'yes' if plan.get('reference_detected') else 'no'}",
        f"- response strategy: {strategy}",
        f"- strategy priority: {priority}",
        f"- strategy action: {action}",
        "- answer the current user move first",
        "- use prior context only when it is relevant",
        "- preserve resolved semantic meaning without copying prior wording",
        "- do not expose internal conversation analysis",
    ]
    if context.get("semantic_facts"):
        lines.append(f"- authoritative semantic context: {context['semantic_facts']}")
    return "\n".join(lines)
