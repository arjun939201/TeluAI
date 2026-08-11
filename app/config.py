import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    GROQ_TOKEN: str = os.getenv(
        "GROQ_TOKEN",
        "",
    )

    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    GROQ_URL: str = os.getenv(
        "GROQ_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    )

    MAX_VOCAB_MATCHES: int = int(
        os.getenv(
            "MAX_VOCAB_MATCHES",
            "12",
        )
    )

    MAX_EXAMPLES: int = int(
        os.getenv(
            "MAX_EXAMPLES",
            "5",
        )
    )

    MAX_GRAMMAR_MATCHES: int = int(
        os.getenv(
            "MAX_GRAMMAR_MATCHES",
            "6",
        )
    )

    MAX_PHRASES: int = int(
        os.getenv(
            "MAX_PHRASES",
            "5",
        )
    )

    MAX_RESPONSE_CHECKS: int = int(
        os.getenv(
            "MAX_RESPONSE_CHECKS",
            "20",
        )
    )

    DATA_DIR: str = os.path.join(
        os.path.dirname(
            os.path.dirname(
                __file__
            )
        ),
        "data",
    )


settings = Settings()


if not settings.GROQ_TOKEN:

    print(
        "WARNING: GROQ_TOKEN is not set."
    )
