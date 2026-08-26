from app.linguistics.normalizer import analyze_input, normalize_roman_telugu


def test_normalizes_short_roman_telugu():
    assert normalize_roman_telugu("ela unnava") == "ఎలా unnava"
    info = analyze_input("ela unnava")
    assert info["roman_telugu_token_count"] == 1
    assert info["roman_telugu_confidence"] > 0


def test_normalizes_common_conversational_tokens():
    info = analyze_input("naaku em kavali")
    assert "నాకు" in info["normalized_hint"]
    assert "ఏం" in info["normalized_hint"]
    assert "కావాలి" in info["normalized_hint"]
    assert info["roman_telugu_token_count"] == 3


def test_preserves_mixed_script_signal():
    info = analyze_input("ఇది Python code ela cheyali")
    assert info["has_telugu_script"] is True
    assert info["has_latin_script"] is True
    assert info["mixed_script"] is True
    assert info["roman_telugu_token_count"] == 2


def test_english_does_not_get_false_roman_confidence():
    info = analyze_input("build a python api")
    assert info["roman_telugu_token_count"] == 0
    assert info["roman_telugu_confidence"] == 0.0
