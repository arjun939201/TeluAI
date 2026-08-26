from app.linguistics.roman_telugu import analyze_roman_telugu


def test_separates_known_and_unknown_roman_telugu():
    result = analyze_roman_telugu("naaku kotha padam kavali")
    assert result["known_tokens"] == ["naaku", "kavali"]
    assert result["unknown_tokens"] == ["kotha", "padam"]
    assert result["confidence"] == 0.5


def test_mixed_script_is_preserved_as_context():
    result = analyze_roman_telugu("ఇది Python ela cheyali")
    assert result["mixed_input"] is True
    assert result["known_tokens"] == ["ela", "cheyali"]
    assert result["has_telugu_output"] is True


def test_unknown_english_does_not_become_language_fact():
    result = analyze_roman_telugu("build a python api")
    assert result["known_tokens"] == []
    assert result["unknown_tokens"] == ["build", "a", "python", "api"]
    assert result["confidence"] == 0.0
