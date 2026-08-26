from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_handles_non_string_values():
    result = analyze_roman_telugu(None)
    assert result["raw"] == ""
    assert result["confidence"] == 0.0
