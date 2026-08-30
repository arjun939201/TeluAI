from app.melimi_engine import PROPERTIES, analyze, compact_report


VOCAB = [
    {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "main_book"},
    {"kind": "VOCABULARY", "key": "వ్యవస్థ", "value": "అమరం", "source": "main_book"},
    {"kind": "VOCABULARY", "key": "అర్థం", "value": "తెల్లం", "source": "main_book"},
]


def test_engine_exposes_deep_analysis_properties():
    required = {
        "source_authority", "canonical_resolution", "inflection_resolution",
        "compound_resolution", "formation_family_analysis", "prefix_boundary_analysis",
        "suffix_boundary_analysis", "semantic_context_analysis", "lexical_collision_detection",
        "transhift_validation", "no_invention_guard", "confidence_tracking",
    }
    assert required <= PROPERTIES.keys()
    assert all(PROPERTIES[key] for key in required)


def test_engine_resolves_canonical_and_inflected_terms():
    result = analyze("ధన్యవాదాన్ని తెలియజేయు", VOCAB)
    assert result.should_transhift
    assert any(x["key"] == "ధన్యవాదం" and x["value"] == "నెనరు" for x in result.matched)
    assert any(x["surface"] == "ధన్యవాదాన్ని" and x["canonical"] == "ధన్యవాదం" for x in result.inflected_matches)
    assert result.should_invent is False


def test_engine_never_invents_on_unknown_term():
    result = analyze("అజ్ఞాతపదాన్ని వాడండి", VOCAB)
    assert not result.should_transhift
    assert result.should_invent is False
    assert "no source-backed match" in compact_report(result)


def test_engine_marks_family_as_evidence_not_productivity():
    vocab = VOCAB + [
        {"kind": "VOCABULARY", "key": "వికానువు", "value": "transformation", "source": "main_book"},
    ]
    result = analyze("వికానువు", vocab)
    assert result.family_candidates
    assert any(x["prefix"] == "వి" for x in result.family_candidates)
    assert any("not unrestricted productivity" in x for x in result.boundaries)
