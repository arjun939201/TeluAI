from app.conversation.planner import plan_response


def test_question_semantics_change_response_plan():
    plan = plan_response({}, {"dominant_signal": "question"})
    assert "answer the question directly" in plan


def test_request_semantics_change_response_plan():
    plan = plan_response({}, {"dominant_signal": "request"})
    assert "fulfill the requested action directly" in plan


def test_negation_semantics_preserve_constraint():
    plan = plan_response({}, {"dominant_signal": "negation"})
    assert "preserve the user's negative constraint" in plan


def test_no_semantic_evidence_preserves_existing_default():
    plan = plan_response({})
    assert plan == "Respond directly to the user's meaning and context. Introduce a question only when conversationally useful."
