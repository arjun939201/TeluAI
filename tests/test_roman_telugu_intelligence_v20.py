from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_has_explicit_unknown_boundary():
    result = analyze_roman_telugu("kotha padam")
    assert result["known_tokens"] == []
    assert result["unknown_tokens"] == ["kotha", "padam"]
