from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_reports_mixed_input_for_telugu_and_latin():
    result = analyze_roman_telugu("ఇది Python")
    assert result["mixed_input"] is True
