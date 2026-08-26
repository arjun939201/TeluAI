from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_counts_only_known_lexical_evidence():
    result = analyze_roman_telugu("nenu api kavali")
    assert result["known_tokens"] == ["nenu", "kavali"]
    assert result["unknown_tokens"] == ["api"]
