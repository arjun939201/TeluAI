from app.linguistics.roman_telugu import analyze_roman_telugu


def test_separates_known_and_unknown_tokens():
    result = analyze_roman_telugu("naaku kotha padam kavali")
    assert result["known_tokens"] == ["naaku", "kavali"]
    assert result["unknown_tokens"] == ["kotha", "padam"]
    assert result["confidence"] == 0.5


def test_preserves_mixed_script_context():
    result = analyze_roman_telugu("ఇది Python ela cheyali")
    assert result["mixed_input"] is True
    assert result["known_tokens"] == ["ela", "cheyali"]


def test_does_not_promote_english_to_roman_telugu():
    result = analyze_roman_telugu("build a python api")
    assert result["known_tokens"] == []
    assert result["confidence"] == 0.0
