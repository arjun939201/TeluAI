from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_returns_raw_and_normalized_forms():
    result = analyze_roman_telugu("naaku kavali")
    assert result["raw"] == "naaku kavali"
    assert result["normalized"] == "నాకు కావాలి"
