"""Regression tests for generic Language Space morphology and sandhi."""
from app.melimi.firewall import deterministic_repair, lexical_violations

def test_am_final_singular_unchanged(): assert deterministic_repair("సినిమా")=="తెఱాటం"
def test_am_final_plural_nominative_uses_aalu_not_amlu(): assert deterministic_repair("సినిమాలు")=="తెఱాటాలు"
def test_am_final_plural_accusative(): assert deterministic_repair("సినిమాలను")=="తెఱాటాలను"
def test_am_final_oblique_plural(): assert deterministic_repair("సినిమాల")=="తెఱాటాల"
def test_am_final_plural_dative(): assert deterministic_repair("సినిమాలకు")=="తెఱాటాలకు"
def test_am_final_plural_instrumental(): assert deterministic_repair("సినిమాలతో")=="తెఱాటాలతో"
def test_am_final_plural_locative(): assert deterministic_repair("సినిమాలలో")=="తెఱాటాలలో"
def test_am_final_singular_accusative_uses_aanni(): assert deterministic_repair("సినిమాను")=="తెఱాటాన్ని"
def test_am_final_singular_dative_uses_aaniki(): assert deterministic_repair("సినిమాకు")=="తెఱాటానికి"
def test_am_final_singular_locative_attaches_directly(): assert deterministic_repair("సినిమాలో")=="తెఱాటంలో"
def test_am_final_singular_instrumental_attaches_directly(): assert deterministic_repair("సినిమాతో")=="తెఱాటంతో"
def test_am_final_sentence_level(): assert deterministic_repair("ఈ సినిమాలు మరియు ఆ సినిమాలను చూశాను.")=="ఈ తెఱాటాలు మరియు ఆ తెఱాటాలను చూశాను."
def test_am_final_rule_is_general_not_hardcoded_to_cinema():
    assert deterministic_repair("వ్యవస్థలు")=="అమరాలు"; assert deterministic_repair("వ్యవస్థలను")=="అమరాలను"
def test_bhasha_root_and_inflection():
    assert deterministic_repair("భాష")=="నుడి"; assert deterministic_repair("భాషలు")=="నుడిలు"; assert deterministic_repair("భాషకు")=="నుడికు"; assert deterministic_repair("భాషలో")=="నుడిలో"
def test_bhasha_derived_form_uses_generic_root_operation():
    assert deterministic_repair("భాషా")=="నుడి"; assert deterministic_repair("ఇది తెలుగు భాషా రూపం.")=="ఇది తెలుగు నుడి రూపం."
def test_aadharita_root(): assert deterministic_repair("ఆధారిత")=="ఆనిద"
def test_adjective_invariant_forms():
    assert deterministic_repair("ఆసక్తికరమైన")=="హాళికాను"; assert deterministic_repair("ఆసక్తికరంగా")=="హాళికానుగా"
def test_violations_report_uses_sandhi_aware_preferred_form():
    assert any(v["source"]=="సినిమాలు" and v["preferred"]=="తెఱాటాలు" for v in lexical_violations("ఈ సినిమాలు బాగున్నాయి."))
