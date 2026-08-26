from app.melimi.morphology_analysis import analyze_morphology, documented_elements, explain_morphology


def test_documented_suffix_returns_authoritative_evidence():
    result = analyze_morphology("పాటకాను")
    assert result["known"] is True
    assert "కాను" in documented_elements("పాటకాను")
    assert result["suffixes"][0]["formations"][0]["status"] == "MASTER"


def test_documented_prefix_returns_evidence():
    result = analyze_morphology("సరిచేయు")
    assert result["known"] is True
    assert "సరి" in documented_elements("సరిచేయు")
    assert result["prefixes"][0]["kind"] == "prefix"


def test_unknown_word_is_not_invented():
    result = analyze_morphology("తెలియనిపదము")
    assert result["known"] is False
    assert result["status"] == "UNKNOWN"
    assert result["evidence"] == []
    assert explain_morphology("తెలియనిపదము") is None


def test_empty_surface_is_safe():
    result = analyze_morphology("")
    assert result["status"] == "EMPTY"
