from app.learner_store import _effective_status


def test_passive_chat_observations_remain_pending():
    for kind in ("sentence", "word_observation", "phrase", "pattern"):
        assert _effective_status(kind, "chat", "approved") == "pending"


def test_explicit_user_learning_can_remain_approved():
    assert _effective_status("vocabulary", "explicit_user", "approved") == "approved"
    assert _effective_status("sentence", "explicit_user", "approved") == "approved"


def test_existing_pending_and_rejected_statuses_are_preserved():
    assert _effective_status("sentence", "chat", "pending") == "pending"
    assert _effective_status("sentence", "chat", "rejected") == "rejected"
