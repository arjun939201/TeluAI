from app.melimi.linguistic_model import analyze_surface
from app.melimi.rules import MelimiRule


def test_rule_requires_authoritative_status_and_supported_operation():
    features = {"number": "plural"}
    assert MelimiRule(name="x", category="morphology", operation="plural", constraints=(("number", "plural"),), status="MASTER", authority="MASTER").supports(features)
    assert not MelimiRule(name="x", category="morphology", operation="plural", constraints=(("number", "plural"),), status="NEEDS_REVIEW", authority="NEEDS_REVIEW").supports(features)
    assert not MelimiRule(name="x", category="morphology", operation="invent", status="MASTER", authority="MASTER").supports(features)


def test_rule_realizes_existing_plural_operation_on_unseen_target_root():
    roots = {"నది": "ఏరు"}
    analysis = analyze_surface("నదులు", roots)
    rule = MelimiRule(
        name="noun-plural",
        category="morphology",
        operation="plural",
        constraints=(("number", "plural"),),
        status="MASTER",
        authority="MASTER",
    )
    assert rule.realize("ఏరు", analysis) == "ఏరులు"


def test_rule_realizes_case_from_abstract_grammatical_feature():
    roots = {"సంతోషం": "అలరిక"}
    analysis = analyze_surface("సంతోషానికి", roots)
    rule = MelimiRule(
        name="noun-dative",
        category="morphology",
        operation="case",
        constraints=(("case", "DATIVE"),),
        status="MASTER",
        authority="MASTER",
    )
    assert rule.realize("అలరిక", analysis) == "అలరికానికి"


def test_rule_does_not_generate_when_analysis_lacks_required_feature():
    analysis = analyze_surface("నది", {"నది": "ఏరు"})
    rule = MelimiRule(
        name="noun-plural",
        category="morphology",
        operation="plural",
        constraints=(("number", "plural"),),
        status="MASTER",
        authority="MASTER",
    )
    assert rule.realize("ఏరు", analysis) is None
