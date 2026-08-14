
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    groq_token: str = os.getenv("GROQ_TOKEN", "").strip()
    groq_url: str = os.getenv(
        "GROQ_URL", "https://api.groq.com/openai/v1/chat/completions"
    ).strip()
    groq_model: str = os.getenv(
        "GROQ_MODEL", "llama-3.1-8b-instant"
    ).strip()
    # Groq free tier for llama-3.1-8b-instant is ~30 RPM / 6,000 TPM (input+
    # output combined) / 14,400 RPD. A previous pass over-corrected for TPM
    # by capping completions at 220 tokens, which cut answers off mid-word
    # (reported: replies ending mid-sentence, e.g. "...ఇది ఒక వినూత").
    # 220 tokens is well under one short paragraph of Telugu. This budget is
    # rebalanced so a normal reply can actually finish, while keeping input
    # context small so a full turn still fits comfortably inside 6,000 TPM.
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "2"))
    max_history_chars_per_turn: int = int(os.getenv("MAX_HISTORY_CHARS_PER_TURN", "200"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "2600"))
    max_memory_items: int = int(os.getenv("MAX_MEMORY_ITEMS", "3"))
    melimi_profile_chars: int = int(os.getenv("MELIMI_PROFILE_CHARS", "450"))
    melimi_relevant_chars: int = int(os.getenv("MELIMI_RELEVANT_CHARS", "750"))
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", "700"))
    max_system_chars: int = int(os.getenv("MAX_SYSTEM_CHARS", "4200"))
    max_user_chars: int = int(os.getenv("MAX_USER_CHARS", "2400"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.70"))
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    melimi_repair_attempts: int = int(os.getenv("MELIMI_REPAIR_ATTEMPTS", "2"))
    github_token: str = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo: str = os.getenv("GITHUB_REPO", "arjun939201/TeluAI").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()
    github_language_file: str = os.getenv(
        "GITHUB_LANGUAGE_FILE", "melimi_telugu/vocabulary/chat_registered.json"
    ).strip()
    github_auto_commit: bool = os.getenv("GITHUB_AUTO_COMMIT", "false").lower() in {"1", "true", "yes", "on"}


settings = Settings()

