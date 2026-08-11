import os

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# SETTINGS
# ============================================================

class Settings:

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    GROQ_TOKEN: str = os.getenv(
        "GROQ_TOKEN",
        "",
    )

    GROQ_URL: str = os.getenv(
        "GROQ_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    )

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    APP_NAME: str = os.getenv(
        "APP_NAME",
        "TeluAI",
    )

    APP_VERSION: str = os.getenv(
        "APP_VERSION",
        "2.0.0",
    )

    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    HOST: str = os.getenv(
        "HOST",
        "0.0.0.0",
    )

    PORT: int = int(
        os.getenv(
            "PORT",
            "8000",
        )
    )

    # --------------------------------------------------------
    # CHAT LIMITS
    # --------------------------------------------------------

    MAX_MESSAGE_LENGTH: int = int(
        os.getenv(
            "MAX_MESSAGE_LENGTH",
            "10000",
        )
    )

    MAX_HISTORY_MESSAGES: int = int(
        os.getenv(
            "MAX_HISTORY_MESSAGES",
            "10",
        )
    )

    MAX_HISTORY_MESSAGE_LENGTH: int = int(
        os.getenv(
            "MAX_HISTORY_MESSAGE_LENGTH",
            "6000",
        )
    )

    MAX_RESPONSE_TOKENS: int = int(
        os.getenv(
            "MAX_RESPONSE_TOKENS",
            "1200",
        )
    )

    # --------------------------------------------------------
    # VOCABULARY
    # --------------------------------------------------------

    VOCABULARY_LIMIT: int = int(
        os.getenv(
            "VOCABULARY_LIMIT",
            "18",
        )
    )

    VOCABULARY_MAX_CHARS: int = int(
        os.getenv(
            "VOCABULARY_MAX_CHARS",
            "6000",
        )
    )

    # --------------------------------------------------------
    # LEARNED CORPUS
    # --------------------------------------------------------

    LEARNED_CONTEXT_LIMIT: int = int(
        os.getenv(
            "LEARNED_CONTEXT_LIMIT",
            "8",
        )
    )

    LEARNED_CONTEXT_MAX_CHARS: int = int(
        os.getenv(
            "LEARNED_CONTEXT_MAX_CHARS",
            "5000",
        )
    )


# ============================================================
# GLOBAL SETTINGS OBJECT
# ============================================================

settings = Settings()


# ============================================================
# VALIDATION
# ============================================================

def validate_settings() -> None:

    if not settings.GROQ_TOKEN:

        raise RuntimeError(
            "GROQ_TOKEN is not configured. "
            "Add GROQ_TOKEN to the environment variables."
        )

    if not settings.GROQ_URL:

        raise RuntimeError(
            "GROQ_URL is not configured."
        )

    if not settings.GROQ_MODEL:

        raise RuntimeError(
            "GROQ_MODEL is not configured."
        )
