from app.melimi.sentence_transformation_service import transform_for_response


def test_response_service_returns_structured_safe_result():
    result = transform_for_response("తెలియనిపదం")
    assert result.source == "తెలియనిపదం"
    assert result.transformed == "తెలియనిపదం"
    assert result.changed_tokens == 0
    assert result.safe
