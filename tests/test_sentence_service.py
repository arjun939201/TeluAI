from app.melimi.sentence_service import transform_sentence


def test_unknown_and_non_telugu_content_is_preserved():
    result = transform_sentence("Hello Python 123")
    assert result["text"] == "Hello Python 123"
    assert result["changed"] is False


def test_trace_is_returned_for_telugu_tokens():
    result = transform_sentence("నమస్కారం!")
    assert result["source"] == "నమస్కారం!"
    assert len(result["trace"]) == 1
    assert "changed" in result["trace"][0]


def test_punctuation_is_preserved():
    result = transform_sentence("ఇది, పరీక్ష.")
    assert result["text"].endswith(".")
    assert "," in result["text"]
