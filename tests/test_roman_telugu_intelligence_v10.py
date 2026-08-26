from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_exposes_normalized_form():
    result = analyze_roman_telugu("naaku kavali")
    assert result["normalized"] == "నాకు కావాలి"
