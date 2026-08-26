from app.melimi.sentence_transformation import transform_sentence, validate_transformation


def test_transforms_supported_root_and_preserves_sentence_shape():
    roots = {"పుస్తకం": "పుస్తకం", "విస్తారం": "విరివి"}
    result = transform_sentence("విస్తారం గురించి చూడు!", roots=roots)
    assert result["transformed"] == "విరివి గురించి చూడు!"
    assert result["changed_tokens"] == 1
    assert result["trace"][0]["status"] == "TRANSFORMED"


def test_reapplies_plural_and_case_operations_from_source_surface():
    roots = {"పుస్తకం": "బుక్క"}
    result = transform_sentence("పుస్తకాలను", roots=roots)
    assert result["trace"][0]["root"] == "పుస్తకం"
    assert result["trace"][0]["target_root"] == "బుక్క"
    assert result["trace"][0]["operations"]
    assert result["transformed"] != "పుస్తకాలను"


def test_unknown_words_are_preserved():
    result = transform_sentence("తెలియనిపదం", roots={})
    assert result["transformed"] == "తెలియనిపదం"
    assert result["unresolved_tokens"] == ["తెలియనిపదం"]


def test_punctuation_and_latin_text_are_preserved():
    result = transform_sentence("Hello, విస్తారం 2026!", roots={"విస్తారం": "విరివి"})
    assert result["transformed"] == "Hello, విరివి 2026!"


def test_validation_rejects_unresolved_operations():
    result = {
        "trace": [
            {"surface": "x", "status": "UNRESOLVED", "operations": [("case", "DATIVE")]}
        ]
    }
    checked = validate_transformation(result)
    assert not checked["valid"]
    assert checked["violations"]
