import pytest

from app.melimi.firewall import deterministic_repair, lexical_violations, reload_firewall


@pytest.fixture(autouse=True)
def _reload():
    reload_firewall()


def test_invariant_adjective_attributive():
    assert deterministic_repair("ఆసక్తికరమైన ఎడాటం") == "హాళికాను ఎడాటం"


def test_invariant_adjective_predicative():
    assert deterministic_repair("ఈ ఎడాటం ఆసక్తికరంగా ఉంది") == "ఈ ఎడాటం హాళికానుగా ఉంది"


def test_existing_plural_inflection_is_preserved():
    assert deterministic_repair("సమస్యలు") == "చిక్కులు"
    assert deterministic_repair("సమస్యలను") == "చిక్కులను"


def test_melimi_derived_word_is_not_treated_as_negation():
    # A complete Melimi formation is a lexical/derivational unit.
    assert deterministic_repair("ముప్పుకాను") == "ముప్పుకాను"


def test_non_melimi_words_are_not_fabricated():
    assert deterministic_repair("తెలియని పదం") == "తెలియని పదం"
