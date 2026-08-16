from app.chat_learning import _content_items, _mapping_pairs, parse_command


def test_normal_chat_mapping_is_detected():
    assert _mapping_pairs("mobile = చేవీనం") == [("mobile", "చేవీనం")]


def test_multiple_mappings_are_detected_without_duplicates():
    text = "mobile = చేవీనం\nద్వేషస్పదం = కంటుపాదు\nmobile = చేవీనం"
    assert _mapping_pairs(text) == [("mobile", "చేవీనం"), ("ద్వేషస్పదం", "కంటుపాదు")]


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
