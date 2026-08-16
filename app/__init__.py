"""TeluAI application package."""

# Install the defensive Language Space presentation deduplicator before
# application routers import the list_space function.
from app import language_space_dedupe as _language_space_dedupe  # noqa: F401
