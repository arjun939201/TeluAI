from __future__ import annotations

from app.database import get_user_settings, recall_user_memory


def settings_for_user(user_id: int) -> dict:
    data = get_user_settings(user_id)
    data["memory"] = recall_user_memory(user_id, limit=8) if data.get("memory_enabled", True) else []
    return data
