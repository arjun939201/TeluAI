from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_identifies_mixed_script_without_losing_roman_tokens():
    result = analyze_roman_telugu("నాకు Python kavali")
    assert result["mixed_input"] is True
    assert result["known_tokens"] == ["kavali"]
