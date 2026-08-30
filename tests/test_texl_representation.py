from app.texl_representation import represent_language, representation_context


VOCAB = [
    {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner"},
]


def test_representation_preserves_authoritative_canonical_evidence():
    result = represent_language("ధన్యవాదం", VOCAB)
    assert result.decision == "RESOLVE_CANONICAL"
    assert result.evidence[0].surface == "ధన్యవాదం"
    assert result.evidence[0].canonical == "ధన్యవాదం"
    assert result.evidence[0].melimi == "నెనరు"
    assert result.evidence[0].authoritative is True
    assert result.should_invent is False


def test_representation_preserves_inflection_without_promoting_surface():
    result = represent_language("ధన్యవాదాన్ని", VOCAB)
    assert result.should_transhift
    assert any(
        item.surface == "ధన్యవాదాన్ని"
        and item.canonical == "ధన్యవాదం"
        and item.melimi == "నెనరు"
        and item.relation == "validated_inflection"
        for item in result.evidence
    )


def test_representation_keeps_unknown_as_unknown():
    result = represent_language("అజ్ఞాతపదం", VOCAB)
    assert result.decision == "UNKNOWN_NO_INVENTION"
    assert result.evidence == ()
    assert result.should_invent is False


def test_representation_context_is_json_safe():
    result = representation_context("ధన్యవాదాన్ని", VOCAB)
    assert result["tokens"] == ["ధన్యవాదాన్ని"]
    assert result["evidence"][0]["canonical"] == "ధన్యవాదం"
