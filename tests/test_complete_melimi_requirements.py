from app.melimi.firewall import deterministic_repair
from app.melimi.grammar import NOUN_SUFFIXES, VERB_SUFFIXES
from app.melimi.index import build_index


def test_language_requirements_are_database_backed():
    paths={d.path for d in build_index()}
    assert "language/rules/core.md" in paths
    assert "language/word_formation/core.md" in paths
    assert "language/vocabulary/core.json" in paths


def test_noun_and_verb_suffix_classes_remain_separate():
    assert "కాను" in NOUN_SUFFIXES and "మారి" in NOUN_SUFFIXES and "వాను" in NOUN_SUFFIXES and "పాదు" in NOUN_SUFFIXES
    assert "అలవి" in VERB_SUFFIXES and "అరిది" in VERB_SUFFIXES
    assert "కాను" not in VERB_SUFFIXES and "అలవి" not in NOUN_SUFFIXES


def test_inflection_preserves_plural_and_case():
    assert deterministic_repair("సమస్య") == "చిక్కు"
    assert deterministic_repair("సమస్యలు") == "చిక్కులు"
    assert deterministic_repair("సమస్యలను") == "చిక్కులను"


def test_invariant_adjective_behavior():
    assert deterministic_repair("ఆసక్తికరమైన ఎడాటం") == "హాళికాను ఎడాటం"
    assert deterministic_repair("ఆసక్తికరంగా ఉంది") == "హాళికానుగా ఉంది"
    assert deterministic_repair("హాళికాను") == "హాళికాను"


def test_derived_melimi_is_not_split_as_negation():
    assert deterministic_repair("ముప్పుకాను") == "ముప్పుకాను"


def test_subject_and_technical_layers_are_present():
    paths={d.path for d in build_index()}
    assert "language/vocabulary/core.json" in paths
    assert "language/examples/core.md" in paths
