from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_preserves_mixed_input_flag():
    result = analyze_roman_telugu("ఇది ela")
    assert result["mixed_input"] is True
