from app.application.workspace_service import (
    LAB_PREFIX,
    LAB_WORKSPACE,
    MAIN_WORKSPACE,
    conversation_belongs_to_workspace,
    normalize_workspace,
)


def test_workspace_normalization_has_safe_main_default():
    assert normalize_workspace(None) == MAIN_WORKSPACE
    assert normalize_workspace("") == MAIN_WORKSPACE
    assert normalize_workspace("unknown") == MAIN_WORKSPACE
    assert normalize_workspace("LAB") == LAB_WORKSPACE


def test_workspace_policy_uses_conversation_identity_not_requested_mode():
    class Conversation:
        def __init__(self, title):
            self.title = title

    main = Conversation("A normal conversation")
    lab = Conversation(f"{LAB_PREFIX}Grammar experiment")

    assert conversation_belongs_to_workspace(main, MAIN_WORKSPACE)
    assert not conversation_belongs_to_workspace(main, LAB_WORKSPACE)
    assert conversation_belongs_to_workspace(lab, LAB_WORKSPACE)
    assert not conversation_belongs_to_workspace(lab, MAIN_WORKSPACE)
    assert not conversation_belongs_to_workspace(None, MAIN_WORKSPACE)
