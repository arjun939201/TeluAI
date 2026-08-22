from app.melimi.language_service import analyze, build_understanding_context


def test_language_service_reads_shared_language_space():
    result = analyze("నమస్కారం ఆసక్తికరమైన విషయం")
    assert "version" in result
    assert isinstance(result["tokens"], list)
    assert result["grammar"]


def test_language_context_is_for_understanding_not_substitution():
    context = build_understanding_context("నమస్కారం")
    assert "MELIMI TELUGU UNDERSTANDING CONTEXT" in context
    assert "language-space version" in context
    assert "RULE: MASTER language knowledge" in context
