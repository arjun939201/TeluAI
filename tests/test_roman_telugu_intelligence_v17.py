from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_detects_telugu_output_for_known_roman_words():
    result = analyze_roman_telugu("naaku")
    assert result["has_telugu_output"] is True
