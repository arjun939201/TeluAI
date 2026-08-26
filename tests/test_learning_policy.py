import pytest

from app.melimi.learning_policy import (
    LanguageConflictError,
    accept_explicit_user_update,
    can_model_promote_to_master,
    can_ordinary_chat_promote_language,
    is_runtime_usable,
    resolve_existing_update,
)


def test_explicit_user_word_can_become_master():
    update = accept_explicit_user_update("కొత్తమాట", "documented meaning")
    assert update.authority == "MASTER"
    assert update.source == "explicit_user"
    assert is_runtime_usable(update.authority)


def test_unapproved_user_update_is_not_runtime_authority():
    update = accept_explicit_user_update("కొత్తమాట", "documented meaning", approved=False)
    assert update.authority == "PROPOSED"
    assert not is_runtime_usable(update.authority)


def test_model_and_ordinary_chat_cannot_promote_language():
    assert can_model_promote_to_master() is False
    assert can_ordinary_chat_promote_language() is False


def test_empty_user_update_rejected():
    with pytest.raises(ValueError):
        accept_explicit_user_update("", "meaning")
    with pytest.raises(ValueError):
        accept_explicit_user_update("word", "")


def test_identical_master_update_is_idempotent():
    update = resolve_existing_update(
        "ఏలువాను",
        "governor",
        existing_meaning="governor",
        existing_authority="MASTER",
    )
    assert update.authority == "MASTER"


def test_conflicting_master_update_requires_correction_workflow():
    with pytest.raises(LanguageConflictError):
        resolve_existing_update(
            "ఏలువాను",
            "different meaning",
            existing_meaning="governor",
            existing_authority="MASTER",
        )


def test_non_master_entry_can_be_explicitly_approved():
    update = resolve_existing_update(
        "కొత్తమాట",
        "documented meaning",
        existing_meaning="old candidate",
        existing_authority="PROPOSED",
    )
    assert update.authority == "MASTER"
    assert update.source == "explicit_user"
