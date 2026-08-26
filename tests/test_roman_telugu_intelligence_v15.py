from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_confidence_reflects_partial_lexical_evidence():
    result = analyze_roman_telugu("naaku kotha kavali")
    assert result["known_count"] == 2
    assert result["unknown_count"] == 1
    assert result["confidence"] == 2 / 3
