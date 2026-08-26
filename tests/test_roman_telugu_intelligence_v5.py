from app.linguistics.roman_telugu import analyze_roman_telugu


def test_known_token_confidence_is_bounded():
    result = analyze_roman_telugu("naaku kavali")
    assert result["confidence"] == 1.0
    assert 0.0 <= result["confidence"] <= 1.0
