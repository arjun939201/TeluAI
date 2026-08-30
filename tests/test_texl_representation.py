from app.texl_representation import classify_translation_intent, represent_language, representation_context


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
        and item.morphology == "accusative"
        and item.grammatical_role == "object"
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
    assert result["evidence"][0]["grammatical_role"] == "object"
    assert result["translation_intent"] == "UNSPECIFIED"


def test_lexical_equivalence_question_returns_canonical_melimi_form():
    message = "ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?"
    assert classify_translation_intent(message) == "LEXICAL_EQUIVALENT"
    result = represent_language(message, VOCAB)
    assert result.translation_intent == "LEXICAL_EQUIVALENT"
    assert result.lexical_equivalent == "నెనరు"
    assert result.regeneration_role is None


def test_sentence_translation_exposes_object_role_without_lexical_question_behavior():
    message = "ధన్యవాదాన్ని తెలియజేయు"
    result = represent_language(message, VOCAB)
    assert result.translation_intent == "UNSPECIFIED"
    assert result.lexical_equivalent is None
    assert result.regeneration_role == "object"


def test_dative_surface_exposes_indirect_object_role():
    result = represent_language("ధన్యవాదానికి", VOCAB)
    item = next(x for x in result.evidence if x.surface == "ధన్యవాదానికి")
    assert item.morphology == "dative"
    assert item.grammatical_role == "indirect_object"
