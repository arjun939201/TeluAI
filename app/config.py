import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    groq_token: str = os.getenv("GROQ_TOKEN", "").strip()
    groq_url: str = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "4"))
    max_history_chars_per_turn: int = int(os.getenv("MAX_HISTORY_CHARS_PER_TURN", "500"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "5000"))
    max_memory_items: int = int(os.getenv("MAX_MEMORY_ITEMS", "6"))
    melimi_profile_chars: int = int(os.getenv("MELIMI_PROFILE_CHARS", "1200"))
    melimi_relevant_chars: int = int(os.getenv("MELIMI_RELEVANT_CHARS", "1800"))
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", "1200"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.45"))
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv("GITHUB_LANGUAGE_FILE", "melimi_telugu/vocabulary/chat_registered.json").strip()
    github_auto_commit: bool = os.getenv("GITHUB_AUTO_COMMIT", "false").lower() in {"1", "true", "yes", "on"}
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    session_days: int = int(os.getenv("SESSION_DAYS", "30"))
    require_auth: bool = os.getenv("REQUIRE_AUTH", "true").lower() in {"1", "true", "yes", "on"}
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "1" if os.getenv("RENDER") else "0").lower() in {"1", "true", "yes", "on"}
    admin_token: str = os.getenv("ADMIN_TOKEN", "").strip()

settings = Settings()
