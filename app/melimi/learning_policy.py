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


class LanguageConflictError(ValueError):
    """Raised when a new teaching conflicts with an established MT entry."""


def accept_explicit_user_update(form: str, meaning: str, *, approved: bool = True) -> LanguageUpdate:
    """Create an authoritative record only for explicit user language teaching.

    Chat-generated guesses must never call this function. Unapproved updates
    remain candidates and cannot directly control production generation.
    """
    form = str(form).strip()
    meaning = str(meaning).strip()
    if not form or not meaning:
        raise ValueError("Both MT form and meaning are required")
    if not approved:
        return LanguageUpdate(form, meaning, "PROPOSED", source="user")
    return LanguageUpdate(form, meaning, "MASTER", source="explicit_user", approved_by="user")


def resolve_existing_update(
    form: str,
    meaning: str,
    *,
    existing_meaning: str | None,
    existing_authority: Authority | None,
    approved: bool = True,
) -> LanguageUpdate:
    """Apply the authority boundary without silently overwriting MASTER data.

    An identical MASTER entry is idempotent. A conflicting MASTER entry is
    rejected unless the caller explicitly uses the project's correction/review
    workflow. Non-MASTER records may be replaced by an explicitly approved
    user teaching.
    """
    update = accept_explicit_user_update(form, meaning, approved=approved)
    if not approved:
        return update
    if existing_authority == "MASTER" and existing_meaning:
        if existing_meaning.strip() == update.meaning.strip():
            return update
        raise LanguageConflictError(
            f"MASTER language entry already exists for {update.form}; use the correction/review workflow"
        )
    return update


def is_runtime_usable(authority: Authority) -> bool:
    """Only authoritative/approved language directly controls production use."""
    return authority == "MASTER"


def can_model_promote_to_master() -> bool:
    return False


def can_ordinary_chat_promote_language() -> bool:
    return False
