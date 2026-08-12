
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
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.78"))


settings = Settings()
