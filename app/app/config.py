
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    GROQ_TOKEN: str = os.getenv("GROQ_TOKEN", "").strip()
    GROQ_URL: str = os.getenv(
        "GROQ_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    ).strip()
    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    ).strip()
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "10"))
    MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "7000"))


settings = Settings()
