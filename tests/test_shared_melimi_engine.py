from app.melimi.engine import build_language_engine_context


def test_melimi_head_contains_shared_understanding_and_generation_context():
    context = build_language_engine_context(
        user_message="నమస్కారం",
        conversation_context="current turn",
        linguistic_analysis="internal analysis",
        response_plan="answer naturally",
        max_profile_chars=1200,
        max_relevant_chars=2400,
    )
    assert "MELIMI TELUGU UNDERSTANDING CONTEXT" in context
    assert "LANGUAGE GENERATION" in context
    assert "UNIFIED MELIMI LANGUAGE SPACE" in context
