import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Known-good Groq production model. Keep the environment variable override,
# but never make an obsolete default the reason Main Chat cannot start.
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


@dataclass(frozen=True)
class Settings:
    groq_token: str = os.getenv("GROQ_API_KEY", os.getenv("GROQ_TOKEN", "")).strip()
    groq_url: str = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
    groq_model: str = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
    groq_fallback_model: str = os.getenv("GROQ_FALLBACK_MODEL", "").strip()
    groq_retry_attempts: int = max(0, int(os.getenv("GROQ_RETRY_ATTEMPTS", "2")))
    groq_max_backoff_seconds: float = max(0.0, float(os.getenv("GROQ_MAX_BACKOFF_SECONDS", "20")))
    groq_enable_fallback: bool = _bool("GROQ_ENABLE_FALLBACK", True)
    groq_max_concurrent_requests: int = max(1, int(os.getenv("GROQ_MAX_CONCURRENT_REQUESTS", "3")))
    max_history_turns: int = max(0, int(os.getenv("MAX_HISTORY_TURNS", "4")))
    max_history_chars_per_turn: int = max(100, int(os.getenv("MAX_HISTORY_CHARS_PER_TURN", "700")))
    max_context_chars: int = max(1000, int(os.getenv("MAX_CONTEXT_CHARS", "5200")))
    max_system_chars: int = max(1000, int(os.getenv("MAX_SYSTEM_CHARS", "4200")))
    max_user_chars: int = max(100, int(os.getenv("MAX_USER_CHARS", "2400")))
    max_memory_items: int = max(0, int(os.getenv("MAX_MEMORY_ITEMS", "8")))
    melimi_profile_chars: int = max(500, int(os.getenv("MELIMI_PROFILE_CHARS", "1500")))
    melimi_relevant_chars: int = max(500, int(os.getenv("MELIMI_RELEVANT_CHARS", "2200")))
    max_response_tokens: int = max(100, int(os.getenv("MAX_RESPONSE_TOKENS", "1400")))
    temperature: float = min(1.5, max(0.0, float(os.getenv("GROQ_TEMPERATURE", "0.35"))))
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv("GITHUB_LANGUAGE_FILE", "database").strip()
    github_auto_commit: bool = _bool("GITHUB_AUTO_COMMIT", False)
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    session_days: int = max(1, int(os.getenv("SESSION_DAYS", "30")))
    require_auth: bool = _bool("REQUIRE_AUTH", True)
    cookie_secure: bool = _bool("COOKIE_SECURE", bool(os.getenv("RENDER")))
    cache_enabled: bool = _bool("CACHE_ENABLED", True)
    cache_min_chars: int = max(1, int(os.getenv("CACHE_MIN_CHARS", "1")))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    trust_proxy_headers: bool = _bool("TRUST_PROXY_HEADERS", bool(os.getenv("RENDER")))
    expose_docs: bool = _bool("EXPOSE_API_DOCS", False)


settings = Settings()
