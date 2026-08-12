from app.language import normalize_roman_telugu, detect_intents


def test_roman_telugu_normalization():
    assert normalize_roman_telugu("haa") == "హా"
    assert normalize_roman_telugu("emle") == "ఏంలేదు"


def test_telugu_is_preserved():
    text = "నమస్కారం"
    assert normalize_roman_telugu(text) == text


def test_intent_detection():
    assert "greeting" in detect_intents("hi")
    assert "acknowledgement" in detect_intents("haa")
