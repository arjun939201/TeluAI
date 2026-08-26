from app.linguistics.roman_telugu import analyze_roman_telugu


def test_empty_input_is_safe():
    result = analyze_roman_telugu("")
    assert result["roman_tokens"] == []
    assert result["confidence"] == 0.0
    assert result["mixed_input"] is False
