from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_preserves_original_input():
    text = "naaku kotha padam kavali"
    result = analyze_roman_telugu(text)
    assert result["raw"] == text
