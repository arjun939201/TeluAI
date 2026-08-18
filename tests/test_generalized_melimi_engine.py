from app.melimi.generalized import GeneralizedMelimiEngine


ROOTS = {
    "నది": "ఏరు",
    "పర్వతం": "కొండ",
    "రహస్యం": "గుట్టు",
    "విస్తారం": "విరివి",
}


def engine():
    return GeneralizedMelimiEngine.from_root_mapping(ROOTS)


def test_root_mapping_is_lexical_knowledge_not_surface_replacement():
    e = engine()
    trace = e.transform_word("నది")
    assert trace.output == "ఏరు"
    assert trace.generalized is False
    assert trace.approved is True
    assert trace.evidence[0].kind == "lexical"


def test_plural_generalizes_to_unseen_surface_form():
    e = engine()
    assert e.transform_word("నదులు").output == "ఏరులు"
    assert e.transform_word("పర్వతాలు").output == "కొండలు"


def test_case_generalizes_from_the_root():
    e = engine()
    assert e.transform_word("నదిలో").output == "ఏరులో"
    assert e.transform_word("నదికి").output == "ఏరుకు"
    assert e.transform_word("పర్వతాలతో").output == "కొండలతో"


def test_derivation_uses_a_reusable_rule_when_supported():
    e = engine()
    trace = e.transform_word("విస్తారమైన")
    assert trace.output == "విరివైన"
    assert trace.generalized is True
    assert any(item.kind == "derivation" for item in trace.evidence)


def test_new_sentence_is_transformed_without_sentence_memorization():
    e = engine()
    source = "మన సీమలో పచ్చని పర్వతాలు, విస్తారమైన నదులు ఉన్నాయి."
    assert e.transform_text(source) == "మన సీమలో పచ్చని కొండలు, విరివైన ఏరులు ఉన్నాయి."


def test_unknown_word_is_preserved_and_not_invented():
    e = engine()
    trace = e.transform_word("తెలియనిపదం")
    assert trace.output == "తెలియనిపదం"
    assert trace.approved is False
    assert trace.evidence == ()


def test_unrelated_near_synonym_is_not_rewritten():
    e = engine()
    assert e.transform_word("సరస్సు").output == "సరస్సు"


def test_explanation_contains_provenance_and_operations():
    e = engine()
    explanation = e.explain_word("నదిలో")
    assert explanation["root"] == "నది"
    assert explanation["melimi_root"] == "ఏరు"
    assert explanation["output"] == "ఏరులో"
    assert explanation["approved"] is True
    assert explanation["operations"]
    assert explanation["evidence"]
