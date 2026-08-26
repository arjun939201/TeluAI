from app.linguistics.roman_telugu import analyze_roman_telugu


def test_known_and_unknown_tokens_are_separate():
    result = analyze_roman_telugu("naaku kotha padam kavali")
    assert result["known_tokens"] == ["naaku", "kavali"]
    assert result["unknown_tokens"] == ["kotha", "padam"]


def test_mixed_script_signal_is_preserved():
    result = analyze_roman_telugu("ఇది Python ela cheyali")
    assert result["mixed_input"] is True
    assert result["known_tokens"] == ["ela", "cheyali"]
