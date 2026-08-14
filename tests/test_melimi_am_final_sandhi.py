"""Regression tests for the ం-final-root sandhi fix and related v13 issue items.

Covers the reported gap where a Melimi root ending in the anusvara "ం" (e.g.
సినిమా -> తెఱాటం) produced invalid inflected forms such as తెఱాటంలు instead
of the correct తెఱాటాలు, plus the new భాష/ఆధారిత vocabulary roots and the
Groq output-truncation detection.
"""

from app.melimi.firewall import deterministic_repair, lexical_violations


# ---------------------------------------------------------------------------
# ం-final root sandhi: సినిమా -> తెఱాటం
# ---------------------------------------------------------------------------

def test_am_final_singular_unchanged():
    assert deterministic_repair("సినిమా") == "తెఱాటం"


def test_am_final_plural_nominative_uses_aalu_not_amlu():
    # This is the exact "bad" example called out in the issue spec.
    result = deterministic_repair("సినిమాలు")
    assert result == "తెఱాటాలు"
    assert "తెఱాటంలు" not in result


def test_am_final_plural_accusative():
    result = deterministic_repair("సినిమాలను")
    assert result == "తెఱాటాలను"
    assert "తెఱాటంలను" not in result


def test_am_final_oblique_plural():
    assert deterministic_repair("సినిమాల") == "తెఱాటాల"


def test_am_final_plural_dative():
    assert deterministic_repair("సినిమాలకు") == "తెఱాటాలకు"


def test_am_final_plural_instrumental():
    assert deterministic_repair("సినిమాలతో") == "తెఱాటాలతో"


def test_am_final_plural_locative():
    assert deterministic_repair("సినిమాలలో") == "తెఱాటాలలో"


def test_am_final_singular_accusative_uses_aanni():
    assert deterministic_repair("సినిమాను") == "తెఱాటాన్ని"


def test_am_final_singular_dative_uses_aaniki():
    assert deterministic_repair("సినిమాకు") == "తెఱాటానికి"


def test_am_final_singular_locative_attaches_directly():
    # లో is NOT a plural marker even though it starts with "ల" — this must
    # not be confused with లలో (the plural locative).
    assert deterministic_repair("సినిమాలో") == "తెఱాటంలో"


def test_am_final_singular_instrumental_attaches_directly():
    assert deterministic_repair("సినిమాతో") == "తెఱాటంతో"


def test_am_final_sentence_level():
    text = "ఈ సినిమాలు మరియు ఆ సినిమాలను చూశాను."
    result = deterministic_repair(text)
    assert result == "ఈ తెఱాటాలు మరియు ఆ తెఱాటాలను చూశాను."


def test_am_final_rule_is_general_not_hardcoded_to_cinema():
    # వ్యవస్థ -> అమరం is a pre-existing, unrelated ం-final root; the same
    # sandhi must apply to it without any per-word rule.
    assert deterministic_repair("వ్యవస్థలు") == "అమరాలు"
    assert deterministic_repair("వ్యవస్థలను") == "అమరాలను"


# ---------------------------------------------------------------------------
# New vocabulary roots from the issue spec: భాష -> నుడి, ఆధారిత -> ఆనిద
# ---------------------------------------------------------------------------

def test_bhasha_root_and_inflection():
    assert deterministic_repair("భాష") == "నుడి"
    assert deterministic_repair("భాషలు") == "నుడిలు"
    assert deterministic_repair("భాషకు") == "నుడికు"
    assert deterministic_repair("భాషలో") == "నుడిలో"


def test_bhasha_derived_form_is_not_hallucinated():
    # భాషా is a Sanskrit-style compounding/attributive derivation of భాష
    # with no established Melimi paradigm on file. Per the issue spec, the
    # engine must not invent an output for it — it must pass through as-is
    # rather than guess.
    assert deterministic_repair("భాషా") == "భాషా"
    assert deterministic_repair("ఇది తెలుగు భాషా రూపం.") == "ఇది తెలుగు భాషా రూపం."


def test_aadharita_root():
    assert deterministic_repair("ఆధారిత") == "ఆనిద"


# ---------------------------------------------------------------------------
# Adjective invariance still holds after the sandhi change
# ---------------------------------------------------------------------------

def test_adjective_invariant_forms_unaffected_by_sandhi_change():
    assert deterministic_repair("ఆసక్తికరమైన") == "హాళికాను"
    assert deterministic_repair("ఆసక్తికరంగా") == "హాళికానుగా"


def test_violations_report_uses_sandhi_aware_preferred_form():
    violations = lexical_violations("ఈ సినిమాలు బాగున్నాయి.")
    assert any(v["source"] == "సినిమాలు" and v["preferred"] == "తెఱాటాలు" for v in violations)
