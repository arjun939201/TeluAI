from app import teluai2_app


def test_chat_prompt_includes_texl_language_representation(monkeypatch):
    monkeypatch.setattr(teluai2_app, "prompt_context", lambda user_id, message="": "")
    monkeypatch.setattr(
        teluai2_app,
        "learned_global",
        lambda limit=80: [
            {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner_chat"}
        ],
    )
    monkeypatch.setattr(
        teluai2_app,
        "choose_output_variety",
        lambda message: type("Decision", (), {"output_variety": type("Variety", (), {"value": "melimi_telugu"})()})(),
    )
    prompt = teluai2_app._build_prompt("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", [], 1, "normal")
    assert "TEX-L భాషా విశ్లేషణ" in prompt
    assert "ధన్యవాదం" in prompt
    assert "నెనరు" in prompt
    assert "LEXICAL_EQUIVALENT" in prompt


def test_chat_prompt_instructs_lexical_equivalent_without_case_transfer():
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(teluai2_app, "prompt_context", lambda user_id, message="": "")
    monkeypatch.setattr(teluai2_app, "learned_global", lambda limit=80: [
        {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner_chat"}
    ])
    monkeypatch.setattr(
        teluai2_app,
        "choose_output_variety",
        lambda message: type("Decision", (), {"output_variety": type("Variety", (), {"value": "melimi_telugu"})()})(),
    )
    prompt = teluai2_app._build_prompt("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", [], 1, "normal")
    assert "కానానికల్ సమానపదాన్ని" in prompt
    monkeypatch.undo()
