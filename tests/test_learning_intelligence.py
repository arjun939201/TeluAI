from app.learning_intelligence import LearningDecision, accepted_suggestions, assess_learning
from app.teluai2_learning import LearningSuggestion


def suggestion() -> LearningSuggestion:
    return LearningSuggestion("VOCABULARY", "సంతోషం", "అలరిక", "explicit user teaching")


def test_learning_requires_explicit_signal():
    decision = assess_learning(suggestion(), role="owner", explicit=False)
    assert decision == LearningDecision(False, "none", "low", "learning was not explicitly indicated")


def test_invalid_suggestion_is_rejected_before_scope_assignment():
    invalid = LearningSuggestion("VOCABULARY", "", "అలరిక", "explicit teaching")
    decision = assess_learning(invalid, role="owner")
    assert decision.accepted is False
    assert decision.scope == "none"
    assert decision.confidence == "low"


def test_owner_learning_is_global_and_high_confidence():
    decision = assess_learning(suggestion(), role="owner")
    assert decision.accepted is True
    assert decision.scope == "global"
    assert decision.confidence == "high"


def test_admin_learning_is_global_and_high_confidence():
    decision = assess_learning(suggestion(), role="admin")
    assert decision.accepted is True
    assert decision.scope == "global"
    assert decision.confidence == "high"


def test_normal_user_learning_is_private_and_medium_confidence():
    decision = assess_learning(suggestion(), role="user")
    assert decision.accepted is True
    assert decision.scope == "user"
    assert decision.confidence == "medium"


def test_accepted_suggestions_filters_rejected_items():
    invalid = LearningSuggestion("VOCABULARY", "", "అలరిక", "bad")
    accepted = accepted_suggestions([suggestion(), invalid], role="user")
    assert len(accepted) == 1
    item, decision = accepted[0]
    assert item == suggestion()
    assert decision.accepted is True
    assert decision.scope == "user"


def test_no_suggestion_is_accepted_without_explicit_learning():
    assert accepted_suggestions([suggestion()], role="owner", explicit=False) == []
