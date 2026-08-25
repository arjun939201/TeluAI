from app.melimi.language_service import _token_record


def _lexicon():
    return {
        "preferred": {"interesting": "హాళికాను", "matter": "ఎడాటం"},
        "registered": {"హాళికాను", "ఎడాటం"},
        "forbidden": {"interesting": "హాళికాను", "matter": "ఎడాటం"},
    }


def test_native_melimi_token_is_resolved_on_melimi_side():
    record = _token_record("హాళికాను", _lexicon(), {"హాళికాను": "interesting", "ఎడాటం": "matter"})
    assert record["known"] is True
    assert record["language_side"] == "melimi"
    assert record["melimi"] == "హాళికాను"
    assert record["matched_root"] == "హాళికాను"


def test_unknown_mt_is_not_reinterpreted_as_standard_telugu():
    record = _token_record("తెలియనిMT", _lexicon(), {"హాళికాను": "interesting", "ఎడాటం": "matter"})
    assert record["known"] is False
    assert record["language_side"] == "unknown"


def test_source_word_still_resolves_for_mixed_language_requests():
    record = _token_record("interesting", _lexicon(), {"హాళికాను": "interesting", "ఎడాటం": "matter"})
    assert record["known"] is True
    assert record["language_side"] == "source"
    assert record["melimi"] == "హాళికాను"
