from app.melimi.formation_rules import (
    LEGACY_AGENT_SUFFIXES,
    can_generate,
    explain_element,
    preferred_agent_suffix,
)


def test_kannu_is_preferred_productive_agent_suffix():
    assert preferred_agent_suffix() == "కాను"
    assert can_generate("కాను")


def test_legacy_agent_suffixes_are_not_productive_for_new_words():
    assert "కాఁడు" in LEGACY_AGENT_SUFFIXES
    assert "గాఁడు" in LEGACY_AGENT_SUFFIXES
    assert "కత్తె" in LEGACY_AGENT_SUFFIXES
    assert not can_generate("కాఁడు")
    assert not can_generate("గాఁడు")
    assert not can_generate("కత్తె")


def test_ari_remains_active():
    assert can_generate("అరి")


def test_kaanu_and_ita_have_documented_evidence():
    agent = explain_element("కాను")
    feminine = explain_element("ఇత")
    assert agent["known"]
    assert any("ముప్పుకాను" in e for f in agent["formations"] for e in f["examples"])
    assert feminine["known"]
    assert "ఏలువానిత" in feminine["formations"][0]["examples"]


def test_prefix_can_have_multiple_documented_senses():
    result = explain_element("అలన్")
    assert result["known"] is True
    functions = {f["function"] for f in result["formations"]}
    assert "గతము" in functions
    assert "మరల మరల" in functions


def test_unknown_formation_is_not_invented():
    assert explain_element("అనిశ్చిత-కల్పన")["known"] is False
