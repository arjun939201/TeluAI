
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
    # Groq free tier is tight (roughly 6,000-12,000 tokens/minute on
    # llama-3.3-70b-versatile). These defaults are kept small on purpose so a
    # normal back-and-forth conversation doesn't blow the per-minute budget
    # in a handful of messages. Raise them only if you're on a paid tier.
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "4"))
    max_history_chars_per_turn: int = int(os.getenv("MAX_HISTORY_CHARS_PER_TURN", "400"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "6500"))
    max_memory_items: int = int(os.getenv("MAX_MEMORY_ITEMS", "6"))
    melimi_profile_chars: int = int(os.getenv("MELIMI_PROFILE_CHARS", "900"))
    melimi_relevant_chars: int = int(os.getenv("MELIMI_RELEVANT_CHARS", "1200"))
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", "900"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.70"))
    melimi_repair_attempts: int = int(os.getenv("MELIMI_REPAIR_ATTEMPTS", "2"))

    # --- Groq resilience settings (rate-limit handling) ---
    # Cheaper/faster model used as an automatic fallback when the primary
    # model is rate-limited. Free-tier TPM budgets are usually much higher
    # on 8b models than on 70b models.
    groq_fallback_model: str = os.getenv(
        "GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant"
    ).strip()
    # How many times to retry the *primary* model on a 429 before falling
    # back. Each retry waits according to Groq's own reset/retry-after
    # headers (capped by groq_max_backoff_seconds).
    groq_retry_attempts: int = int(os.getenv("GROQ_RETRY_ATTEMPTS", "2"))
    groq_max_backoff_seconds: float = float(os.getenv("GROQ_MAX_BACKOFF_SECONDS", "20"))
    # Whether to try the fallback model at all when the primary keeps 429ing.
    groq_enable_fallback: bool = os.getenv("GROQ_ENABLE_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
    # Caps how many Groq requests this process will have in flight at once,
    # so a burst of concurrent users doesn't all slam the TPM ceiling at the
    # same instant. Requests beyond this queue up instead of firing together.
    groq_max_concurrent_requests: int = int(os.getenv("GROQ_MAX_CONCURRENT_REQUESTS", "3"))

    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv(
        "GITHUB_LANGUAGE_FILE", "melimi_telugu/vocabulary/chat_registered.json"
    ).strip()
    github_auto_commit: bool = os.getenv("GITHUB_AUTO_COMMIT", "false").lower() in {"1", "true", "yes", "on"}


settings = Settings()
