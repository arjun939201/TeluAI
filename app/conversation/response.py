"""Conversation-aware response instructions."""
from __future__ import annotations

from typing import Any


def build_response_context(plan: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    """Build concise internal guidance for natural, context-aware responses."""
    context = context or {}
    lines = [
        "CONVERSATIONAL RESPONSE GUIDANCE:",
        f"- current intent: {plan.get('intent', 'unknown')}",
        f"- topic relation: {plan.get('topic_relation', 'unknown')}",
        f"- established topic: {plan.get('topic') or '(none)'}",
        f"- open question: {plan.get('open_question') or '(none)'}",
        f"- reference detected: {'yes' if plan.get('reference_detected') else 'no'}",
        "- answer the current user move first",
        "- use prior context only when it is relevant",
        "- preserve resolved semantic meaning without copying prior wording",
        "- do not expose internal conversation analysis",
    ]
    if context.get("semantic_facts"):
        lines.append(f"- authoritative semantic context: {context['semantic_facts']}")
    return "\n".join(lines)
