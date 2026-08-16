"""TeluAI application package."""

# Install presentation deduplication and chat-learning hooks before FastAPI
# routers import the affected helpers.
from app import language_space_dedupe as _language_space_dedupe  # noqa: F401
from app import chat_learning_runtime as _chat_learning_runtime  # noqa: F401

_chat_learning_runtime.install()
