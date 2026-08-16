"""TeluAI application package."""

# Install persistence/content overrides before app.main imports functions from
# app.database. This keeps the current architecture while moving Melimi data
# ownership to PostgreSQL.
from app import runtime_overrides as _runtime_overrides  # noqa: F401
