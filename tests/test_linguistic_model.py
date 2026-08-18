from app.melimi.linguistic_model import (
    LinguisticAnalysis,
    MorphologicalFeatures,
    lexical_entry,
    analyze_surface,
    transform_surface,
)


def test_lexical_entry_is_lemma_level_and_structured():
    entry = lexical_entry(
        "నది",
        "ఏరు",
        metadata={
            "part_of_speech": "noun",
            "semantic_class": "natural_feature",
            "morphological_class": "noun_am",
            "inflection_class": "productive_noun",
            "source": "master_corpus",
            "status": "MASTER",
            "version": 12,
        },
    )
    assert entry.standard_lemma == "నది"
    assert entry.melimi_lemma == "ఏరు"
    assert entry.part_of_speech == "noun"
    assert entry.semantic_class == "natural_feature"
    assert entry.inflection_class == "productive_noun"
    assert entry.authority == "MASTER"
    assert entry.version == 12


def test_surface_analysis_exposes_features_without_guessing():
    analysis = analyze_surface("సమస్యలను", {"సమస్య": "చిక్కు"})
    assert isinstance(analysis, LinguisticAnalysis)
    assert analysis.root == "సమస్య"
    assert analysis.features.number == "plural"
    assert analysis.features.case == "ACCUSATIVE"
    assert analysis.features.tense is None
    assert analysis.features.person is None


def test_unseen_inflected_instance_is_generated_from_lemma_mapping():
    roots = {"సమస్య": "చిక్కు"}
    result = transform_surface("సమస్యలకు", roots)
    assert result.status == "MASTER"
    assert result.source_lemma == "సమస్య"
    assert result.target_lemma == "చిక్కు"
    assert result.target_surface == "చిక్కుకు"
    assert result.analysis.features.number == "plural"
    assert result.analysis.features.case == "DATIVE"
    assert result.generated is True


def test_unknown_surface_is_preserved_and_marked_unsupported():
    result = transform_surface("తెలియనిపదం", {"సమస్య": "చిక్కు"})
    assert result.status == "UNSUPPORTED"
    assert result.target_surface == "తెలియనిపదం"
    assert result.target_lemma == ""
    assert result.evidence is None


def test_features_are_explicit_and_serializable():
    features = MorphologicalFeatures(number="plural", case="LOCATIVE")
    payload = features.as_dict()
    assert payload["number"] == "plural"
    assert payload["case"] == "LOCATIVE"
    assert payload["tense"] is None
