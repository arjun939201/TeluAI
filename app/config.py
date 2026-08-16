import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    groq_token: str = os.getenv("GROQ_API_KEY", os.getenv("GROQ_TOKEN", "")).strip()
    groq_url: str = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "4"))
    max_history_chars_per_turn: int = int(os.getenv("MAX_HISTORY_CHARS_PER_TURN", "700"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "5200"))
    max_system_chars: int = int(os.getenv("MAX_SYSTEM_CHARS", "4200"))
    max_memory_items: int = int(os.getenv("MAX_MEMORY_ITEMS", "8"))
    melimi_profile_chars: int = int(os.getenv("MELIMI_PROFILE_CHARS", "1500"))
    melimi_relevant_chars: int = int(os.getenv("MELIMI_RELEVANT_CHARS", "2200"))
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", "1400"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.35"))
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv("GITHUB_LANGUAGE_FILE", "database").strip()
    github_auto_commit: bool = os.getenv("GITHUB_AUTO_COMMIT", "false").lower() in {"1","true","yes","on"}
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    session_days: int = int(os.getenv("SESSION_DAYS", "30"))
    require_auth: bool = os.getenv("REQUIRE_AUTH", "true").lower() in {"1","true","yes","on"}
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "1" if os.getenv("RENDER") else "0").lower() in {"1","true","yes","on"}
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() in {"1","true","yes","on"}
    cache_min_chars: int = int(os.getenv("CACHE_MIN_CHARS", "1"))

settings=Settings()
# TELUAI_OWNER_EMAIL is intentionally read at bootstrap time from the environment
# so it can be removed after the first owner is established.
