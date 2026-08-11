import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_TOKEN: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    GROQ_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    MAX_VOCAB_MATCHES: int = int(os.getenv("MAX_VOCAB_MATCHES", "8"))
    MAX_EXAMPLES: int = int(os.getenv("MAX_EXAMPLES", "5"))

    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


settings = Settings()

if not settings.GROQ_TOKEN:
    print("WARNING: GROQ_TOKEN is not set. Add your Groq token to the environment.")
