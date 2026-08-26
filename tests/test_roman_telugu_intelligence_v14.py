from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_exposes_unknown_count():
    result = analyze_roman_telugu("naaku kotha padam")
    assert result["unknown_count"] == 2
