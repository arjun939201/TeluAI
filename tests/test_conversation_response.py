from app.conversation.response import build_response_context


def test_question_uses_direct_answer_strategy():
    guidance = build_response_context({"intent": "what_question", "dominant_signal": "question"})
    assert "response strategy: answer" in guidance
    assert "answer the current question directly" in guidance


def test_request_uses_fulfillment_strategy():
    guidance = build_response_context({"intent": "request", "dominant_signal": "request"})
    assert "response strategy: fulfill" in guidance
    assert "fulfill the current request directly" in guidance


def test_reference_takes_priority_over_generic_strategy():
    guidance = build_response_context({"intent": "contextual_statement", "reference_detected": True})
    assert "response strategy: resolve_reference" in guidance


def test_negative_constraint_is_preserved():
    guidance = build_response_context({"intent": "nothing_or_negative", "dominant_signal": "negation"})
    assert "response strategy: respect_constraint" in guidance
    assert "negative or stopping constraint" in guidance
