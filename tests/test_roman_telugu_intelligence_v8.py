from app.linguistics.roman_telugu import analyze_roman_telugu


def test_unknown_words_are_not_normalized_as_facts():
    result = analyze_roman_telugu("kotha padam")
    assert result["unknown_tokens"] == ["kotha", "padam"]
    assert result["normalized"] == "kotha padam"
