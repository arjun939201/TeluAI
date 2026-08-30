from app.texl_brain import analyze_language

VOCAB = [
    {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner"},
]


def test_brain_resolves_canonical_word():
    result = analyze_language("ధన్యవాదం", VOCAB)
    assert result.decision == "RESOLVE_CANONICAL"
    assert result.evidence[0].canonical == "ధన్యవాదం"
    assert result.evidence[0].melimi == "నెనరు"
    assert result.evidence[0].authoritative


def test_brain_resolves_am_accusative_surface_to_canonical():
    result = analyze_language("ధన్యవాదాన్ని", VOCAB)
    assert result.decision == "RESOLVE_CANONICAL"
    assert any(x.relation == "validated_inflection" and x.canonical == "ధన్యవాదం" for x in result.evidence)


def test_brain_does_not_invent_unknown_word():
    result = analyze_language("అజ్ఞాతపదం", VOCAB)
    assert result.decision == "UNKNOWN_NO_INVENTION"
    assert result.analysis.should_invent is False
    assert result.evidence == ()


def test_family_evidence_is_not_authority():
    result = analyze_language("ధన్యవాదం", VOCAB)
    assert all(x.relation != "family_candidate" or not x.authoritative for x in result.evidence)
