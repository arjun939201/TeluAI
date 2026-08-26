from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_does_not_modify_source_text():
    source = "naaku kotha padam"
    result = analyze_roman_telugu(source)
    assert result["raw"] == source
