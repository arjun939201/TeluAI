from app.melimi.corpus_rules import (
    ADJECTIVE_SUFFIXES,
    CORPUS_EXAMPLES,
    DERIVATIONAL_SUFFIXES,
    LEXICAL_PARADIGMS,
    MUNUJERPULU,
    NEW_MUNUJERPULU,
    PADAGRAMULU,
    corpus_manifest,
)
from app.melimi.root_morphology import convert_surface, reduce_to_root


def test_corpus_manifest_and_rule_families_exist():
    manifest = corpus_manifest()
    assert manifest["status"] == "MASTER_RULESET"
    assert "మునుజేర్పులు" in manifest["sections"]
    assert "కాను" in DERIVATIONAL_SUFFIXES
    assert "వాను" in DERIVATIONAL_SUFFIXES
    assert "అల్వి" in DERIVATIONAL_SUFFIXES
    assert "మైన" not in DERIVATIONAL_SUFFIXES
    assert "పు" in ADJECTIVE_SUFFIXES
    assert "అడి" in MUNUJERPULU
    assert "సరి" in NEW_MUNUJERPULU
    assert "దరి" in PADAGRAMULU
    assert "విషయం" in LEXICAL_PARADIGMS
    assert "కంటుపాదు" in CORPUS_EXAMPLES


def test_common_am_noun_plural_is_regenerated_from_target_root():
    roots = {"విషయం": "ఎడాటం", "పదం": "పలుకు"}
    assert convert_surface("విషయం", roots) == "ఎడాటం"
    assert convert_surface("విషయాలు", roots) == "ఎడాటాలు"
    assert convert_surface("విషయాలను", roots) == "ఎడాటాలను"
    assert convert_surface("పదం", roots) == "పలుకు"
    assert convert_surface("పదాలు", roots) == "పలుకులు"
    assert convert_surface("పదాలను", roots) == "పలుకులను"


def test_adjectival_and_relational_derivation_is_regenerated():
    roots = {
        "భాష": "నుడి",
        "వ్యాకరణం": "జక్కం",
        "స్థాపితం": "నెలగొల్పిదం",
    }
    assert convert_surface("భాషా", roots) == "నుడి"
    assert convert_surface("వ్యాకరణ", roots) == "జక్క"
    assert convert_surface("వ్యాకరణపు", roots) == "జక్కపు"
    assert convert_surface("స్థాపితమైన", roots) == "నెలగొల్పిదమైన"


def test_plural_form_is_recognized_as_the_source_root():
    roots = {"విషయం": "ఎడాటం"}
    form = reduce_to_root("విషయాలు", roots)
    assert form.root == "విషయం"
    assert form.operations == (("plural", "ాలు"),)
