from app.teluai2_learning import _is_relevant, _normalize_telugu_term, _relevance_terms


def test_common_telugu_plural_normalizes_to_base_form():
    assert _normalize_telugu_term("నెనరులు") == "నెనరు"


def test_inflected_query_matches_explicitly_learned_base_word():
    item = {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు"}
    assert _is_relevant(item, _relevance_terms("TeluAI కు నెనరులు"))


def test_unrelated_learning_does_not_match_short_query():
    item = {"kind": "VOCABULARY", "key": "కాంచువు", "value": "అధ్యాపకుడు"}
    assert not _is_relevant(item, _relevance_terms("TeluAI కు నెనరులు"))
