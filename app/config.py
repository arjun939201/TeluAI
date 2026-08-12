
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    groq_token: str = os.getenv("GROQ_TOKEN", "").strip()
    groq_url: str = os.getenv(
        "GROQ_URL", "https://api.groq.com/openai/v1/chat/completions"
    ).strip()
    groq_model: str = os.getenv(
        "GROQ_MODEL", "llama-3.3-70b-versatile"
    ).strip()
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "6500"))
    max_memory_items: int = int(os.getenv("MAX_MEMORY_ITEMS", "12"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.70"))
    melimi_repair_attempts: int = int(os.getenv("MELIMI_REPAIR_ATTEMPTS", "2"))
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv(
        "GITHUB_LANGUAGE_FILE", "melimi_telugu/vocabulary/chat_registered.json"
    ).strip()
    github_auto_commit: bool = os.getenv("GITHUB_AUTO_COMMIT", "true").lower() in {"1", "true", "yes", "on"}


settings = Settings()
