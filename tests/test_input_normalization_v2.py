from app.linguistics.normalizer import analyze_input


def test_roman_telugu_normalization():
    info = analyze_input("naaku em kavali")
    assert "నాకు" in info["normalized_hint"]
    assert "ఏం" in info["normalized_hint"]
    assert "కావాలి" in info["normalized_hint"]
    assert info["roman_telugu_token_count"] == 3


def test_mixed_script_signal():
    info = analyze_input("ఇది Python code ela cheyali")
    assert info["mixed_script"] is True
    assert info["roman_telugu_token_count"] == 2


def test_english_has_no_roman_telugu_signal():
    info = analyze_input("build a python api")
    assert info["roman_telugu_token_count"] == 0
    assert info["roman_telugu_confidence"] == 0.0
