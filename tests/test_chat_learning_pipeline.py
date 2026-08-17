from app.chat_learning import _content_items, _mapping_pairs, parse_command


def test_normal_chat_mapping_is_detected():
    assert _mapping_pairs("mobile = చేవీనం") == [("mobile", "చేవీనం")]


def test_multiple_mappings_are_detected_without_duplicates():
    text = "mobile = చేవీనం\nద్వేషస్పదం = కంటుపాదు\nmobile = చేవీనం"
    assert _mapping_pairs(text) == [("mobile", "చేవీనం"), ("ద్వేషస్పదం", "కంటుపాదు")]


def test_loan_native_label_is_metadata_not_part_of_word():
    text = "ద్వేషస్పదం (sanskrit based loan word) = కంటుపాదు"
    assert _mapping_pairs(text) == [("ద్వేషస్పదం", "కంటుపాదు")]


def test_content_extracts_words_phrases_sentences_and_patterns():
    words, phrases, patterns = _content_items("ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి.")
    assert "ముప్పుకాను" in words
    assert phrases
    assert patterns


def test_command_parser_remains_supported():
    kind, payload = parse_command("/word mobile = చేవీనం")
    assert kind == "word"
    assert payload["source"] == "mobile"
    assert payload["melimi"] == "చేవీనం"


def test_bulk_word_command_preserves_every_mapping():
    kind, payload = parse_command("/word సంబంధం = తౌలం; ప్రకారం = బట్టి; ఉదాహరణ = మచ్చుక")
    assert kind == "word"
    assert payload["bulk"] is True
    assert payload["count"] == 3
    assert payload["mappings"] == [
        {"source": "సంబంధం", "melimi": "తౌలం"},
        {"source": "ప్రకారం", "melimi": "బట్టి"},
        {"source": "ఉదాహరణ", "melimi": "మచ్చుక"},
    ]
