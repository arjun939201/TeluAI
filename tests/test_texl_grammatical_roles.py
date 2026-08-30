from app.texl_representation import represent_language

VOCAB = [
    {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner"},
]


def test_lexical_question_suppresses_source_case_regeneration():
    result = represent_language("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", VOCAB)
    assert result.translation_intent == "LEXICAL_EQUIVALENT"
    assert result.lexical_equivalent == "నెనరు"
    assert result.regeneration_role is None


def test_sentence_context_exposes_validated_object_role():
    result = represent_language("ధన్యవాదాన్ని తెలియజేయు", VOCAB)
    assert result.translation_intent == "UNSPECIFIED"
    assert result.regeneration_role == "object"
    evidence = next(x for x in result.evidence if x.surface == "ధన్యవాదాన్ని")
    assert evidence.morphology == "accusative"
    assert evidence.grammatical_role == "object"


def test_dative_surface_exposes_indirect_object_role():
    result = represent_language("ధన్యవాదానికి", VOCAB)
    evidence = next(x for x in result.evidence if x.surface == "ధన్యవాదానికి")
    assert evidence.morphology == "dative"
    assert evidence.grammatical_role == "indirect_object"
