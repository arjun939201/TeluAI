from app import teluai2_learning
from app.teluai2_learning import LearningSuggestion, _is_relevant, _relevance_terms


def test_relevance_terms_extract_telugu_and_english_terms():
    terms = _relevance_terms("ఈ పదం గురించి happiness చెప్పు")
    assert "ఈ" in terms
    assert "పదం" in terms
    assert "happiness" in terms


def test_is_relevant_matches_learned_word_or_value():
    item = {"kind": "VOCABULARY", "key": "సంతోషం", "value": "అలరిక", "source": "owner_chat"}
    assert _is_relevant(item, {"సంతోషం"})
    assert _is_relevant(item, {"అలరిక"})
    assert not _is_relevant(item, {"వేరే"})


def test_prompt_context_keeps_unrelated_global_learning_out(monkeypatch):
    monkeypatch.setattr(
        teluai2_learning,
        "learned_global",
        lambda limit=80: [
            {"kind": "VOCABULARY", "key": "సంతోషం", "value": "అలరిక", "source": "owner_chat"},
            {"kind": "VOCABULARY", "key": "ఇల్లు", "value": "గృహం", "source": "owner_chat"},
        ],
    )
    monkeypatch.setattr(teluai2_learning, "learned_for_user", lambda user_id, limit=40: [])
    context = teluai2_learning.prompt_context(1, message="సంతోషం")
    assert "సంతోషం" in context
    assert "ఇల్లు" not in context


def test_prompt_context_uses_small_recent_fallback_without_message(monkeypatch):
    monkeypatch.setattr(
        teluai2_learning,
        "learned_global",
        lambda limit=80: [
            {"kind": "VOCABULARY", "key": "సంతోషం", "value": "అలరిక", "source": "owner_chat"},
        ],
    )
    monkeypatch.setattr(teluai2_learning, "learned_for_user", lambda user_id, limit=40: [])
    context = teluai2_learning.prompt_context(1)
    assert "సంతోషం" in context
