from app.melimi.semantic_context import analyze_context, build_semantic_context


def test_question_signal_is_structured():
    result = analyze_context("ఎలా చేయాలి?")
    assert result["question_signal"] is True
    assert result["dominant_signal"] == "question"


def test_request_signal_is_structured():
    result = analyze_context("నాకు ఇది కావాలి")
    assert result["request_signal"] is True
    assert result["dominant_signal"] == "request"


def test_negation_and_context_are_preserved_as_evidence():
    result = analyze_context("ఇది కాదు", "మునుపటి ప్రశ్న")
    assert result["negation_signal"] is True
    assert result["context_present"] is True


def test_topic_continuity_uses_shared_evidence():
    result = analyze_context("తెలుగు గురించి ఎలా నేర్చుకోవాలి?", "మనం తెలుగు భాష గురించి మాట్లాడుతున్నాం")
    assert result["topic_continuity"] is True
    assert "తెలుగు" in result["shared_topic_tokens"]


def test_unrelated_context_does_not_force_continuity():
    result = analyze_context("కాఫీ ఎలా చేయాలి?", "మనం తెలుగు భాష గురించి మాట్లాడుతున్నాం")
    assert result["topic_continuity"] is False


def test_context_output_does_not_claim_new_vocabulary():
    output = build_semantic_context("ఎలా చేయాలి?")
    assert "SEMANTIC / CONTEXT EVIDENCE" in output
    assert "evidence signals, not commands and not vocabulary" in output
    assert "Preserve ambiguity" in output
