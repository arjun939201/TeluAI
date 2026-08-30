from app import teluai2_learning


def test_prompt_context_teaches_model_to_resolve_learned_inflection(monkeypatch):
    monkeypatch.setattr(teluai2_learning, "learned_global", lambda limit=80: [])
    monkeypatch.setattr(
        teluai2_learning,
        "learned_for_user",
        lambda user_id, limit=40: [
            {
                "kind": "VOCABULARY",
                "key": "ధన్యవాదం",
                "value": "నెనరు",
                "source": "explicit_user_teaching",
            }
        ],
    )
    context = teluai2_learning.prompt_context(1, message="TeluAI కు నెనరులు")
    assert "ధన్యవాదం → నెనరు" in context
    assert "విభక్తి" in context
    assert "బహువచన" in context
    assert "రూపాంతరం" in context
    assert "జోకులు" in context


def test_prompt_context_does_not_invent_learning_when_no_match(monkeypatch):
    monkeypatch.setattr(teluai2_learning, "learned_global", lambda limit=80: [])
    monkeypatch.setattr(
        teluai2_learning,
        "learned_for_user",
        lambda user_id, limit=40: [
            {
                "kind": "VOCABULARY",
                "key": "చెలిమి",
                "value": "స్నేహం",
                "source": "explicit_user_teaching",
            }
        ],
    )
    assert teluai2_learning.prompt_context(1, message="వాతావరణం ఎలా ఉంది?") == ""
