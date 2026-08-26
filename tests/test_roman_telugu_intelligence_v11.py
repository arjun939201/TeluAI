from app.linguistics.roman_telugu import analyze_roman_telugu


def test_analysis_is_json_serializable_shape():
    result = analyze_roman_telugu("ela cheyali")
    assert isinstance(result["roman_tokens"], list)
    assert isinstance(result["known_tokens"], list)
    assert isinstance(result["unknown_tokens"], list)
