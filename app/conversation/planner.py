from typing import Dict


def plan_natural_response(understanding: Dict[str, object]) -> str:
    intent = str(understanding.get("intent", ""))

    if intent == "clarification_request":
        return (
            "Clarify what the assistant just asked or meant. "
            "Do not reinterpret the clarification as a new subject."
        )

    if intent == "agreement":
        return (
            "Acknowledge the agreement naturally. Continue only if the "
            "conversation gives a reason; do not automatically ask another generic question."
        )

    if intent == "acknowledgement":
        return (
            "Treat this as an acknowledgement whose exact meaning depends on context. "
            "Respond to the previous turn rather than inventing a new topic."
        )

    if intent == "continue_request":
        return (
            "Continue the current topic or explain further. Do not restart the conversation."
        )

    return (
        "Answer the user's current meaning in context. Prefer a direct, natural turn "
        "over a generic conversation starter."
    )
