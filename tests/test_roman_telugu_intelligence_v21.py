from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_handles_whitespace():
    result = analyze_roman_telugu("  naaku   kavali  ")
    assert result["raw"] == "naaku   kavali"
    assert result["known_count"] == 2
