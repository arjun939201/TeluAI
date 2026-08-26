from app.linguistics.roman_telugu import analyze_roman_telugu


def test_english_is_not_promoted_to_roman_telugu():
    result = analyze_roman_telugu("build a python api")
    assert result["known_tokens"] == []
    assert result["confidence"] == 0.0
