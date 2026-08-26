from app.linguistics.roman_telugu import analyze_roman_telugu


def test_telugu_script_is_detected_after_normalization():
    result = analyze_roman_telugu("ela unnava")
    assert result["has_telugu_output"] is True
