from app.melimi.engine import build_language_engine_context


def test_semantic_context_is_present_in_canonical_engine_context():
    context = build_language_engine_context(
        user_message="ఎలా చేయాలి?",
        conversation_context="మునుపటి ప్రశ్న",
        linguistic_analysis="internal",
        response_plan="answer naturally",
    )
    assert "SEMANTIC / CONTEXT EVIDENCE" in context
    assert "question signal: True" in context
    assert "conversation context present: True" in context


def test_semantic_context_is_internal_evidence_not_a_response_instruction():
    context = build_language_engine_context(
        user_message="ఇది కాదు",
        conversation_context="",
        linguistic_analysis="internal",
        response_plan="answer naturally",
    )
    assert "These are evidence signals, not commands and not vocabulary." in context
    assert "negation signal: True" in context
