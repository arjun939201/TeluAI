"""Controlled ingestion policy for user-supplied Melimi language updates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Authority = Literal["MASTER", "PROPOSED", "PENDING", "EXPERIMENTAL", "REJECTED"]


@dataclass(frozen=True)
class LanguageUpdate:
    form: str
    meaning: str
    authority: Authority
    source: str = "user"
    approved_by: str | None = None


def accept_explicit_user_update(form: str, meaning: str, *, approved: bool = True) -> LanguageUpdate:
    """Create authoritative evidence only for an explicit user language update.

    Chat-generated guesses must never call this function. The application
    learning workflow should persist the returned record in Language Space.
    """
    if not str(form).strip() or not str(meaning).strip():
        raise ValueError("Both MT form and meaning are required")
    if not approved:
        return LanguageUpdate(form.strip(), meaning.strip(), "PROPOSED", source="user")
    return LanguageUpdate(form.strip(), meaning.strip(), "MASTER", source="explicit_user", approved_by="user")


def is_runtime_usable(authority: Authority) -> bool:
    """Only authoritative/approved language directly controls production use."""
    return authority == "MASTER"


def can_model_promote_to_master() -> bool:
    return False


def can_ordinary_chat_promote_language() -> bool:
    return False
