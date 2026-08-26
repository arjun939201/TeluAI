import pytest

from app.melimi.learning_policy import (
    accept_explicit_user_update,
    can_model_promote_to_master,
    can_ordinary_chat_promote_language,
    is_runtime_usable,
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
