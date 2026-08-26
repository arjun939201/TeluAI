from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_reports_known_count():
    result = analyze_roman_telugu("naaku kavali")
    assert result["known_count"] == 2
    assert result["unknown_count"] == 0
