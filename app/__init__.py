"""TeluAI application package."""

# Install persistence/content overrides before app.main imports functions from
# app.database. This keeps the current architecture while moving Melimi data
# ownership to PostgreSQL.
from app import runtime_overrides as _runtime_overrides  # noqa: F401

# Install the explicit chat-learning hook once the persistence layer is ready.
# It learns only recognizable teaching forms (mappings and paired examples),
# never ordinary conversational turns.
from app.chat_learning import install_chat_learning as _install_chat_learning
_install_chat_learning()
