from app.melimi.engine import build_language_engine_context


def test_engine_includes_documented_morphology_evidence():
    context = build_language_engine_context(
        user_message="తెలుసుకోవాలి",
        conversation_context="",
        linguistic_analysis="",
        response_plan="Answer helpfully.",
    )
    assert "MORPHOLOGY EVIDENCE" in context
    assert "corpus-backed" in context


def test_engine_does_not_treat_unknown_morphology_as_established():
    context = build_language_engine_context(
        user_message="zzunknownword",
        conversation_context="",
        linguistic_analysis="",
        response_plan="Answer helpfully.",
    )
    assert "MORPHOLOGY EVIDENCE" in context
    assert "unknown" in context.lower()
