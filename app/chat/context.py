from __future__ import annotations

from app.database import recall_user_memory, get_history


def build_context(user_id: int, conversation_id: str | None, *, memory_enabled: bool = True,
                  recent_limit: int = 16, recent_chars: int = 5000) -> tuple[list[dict], str, list[dict]]:
    """Build a bounded model context without replaying the whole database.

    The conversation summary is stored on the conversation record and is kept
    separate from recent turns. Memory is explicit, user-owned data only.
    """
    if not conversation_id:
        history: list[dict] = []
        summary = ""
    else:
        rows = get_history(user_id, conversation_id, limit=recent_limit)
        history = [
            {"role": item["role"], "content": str(item["content"])[:recent_chars]}
            for item in rows[-recent_limit:]
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]
        # get_history intentionally returns messages only; the summary is
        # fetched by the caller when needed to avoid a second expensive join.
        summary = ""
    memories = recall_user_memory(user_id) if memory_enabled else []
    return history, summary, memories


def format_memory(memories: list[dict], max_items: int = 8) -> str:
    if not memories:
        return ""
    lines = ["USER-CONTROLLED MEMORY (use only when directly relevant):"]
    for item in memories[:max_items]:
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()
        if key and value:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)
