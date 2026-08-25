from app.chat.router import route_message


def test_telugu_conversation_uses_melimi_path_by_default():
    decision = route_message("నాకు artificial intelligence గురించి చెప్పు", "auto")
    assert decision.language == "mixed"
    assert decision.use_melimi is True
    assert decision.mode == "melimi"
    assert decision.explicit is False


def test_roman_telugu_conversation_uses_melimi_path_by_default():
    decision = route_message("naaku AI gurinchi cheppu", "auto")
    assert decision.language == "roman_telugu"
    assert decision.use_melimi is True
    assert decision.mode == "melimi"


def test_english_conversation_uses_native_melimi_path_by_default():
    decision = route_message("How do I explain this Python function?", "auto")
    assert decision.language == "english"
    assert decision.mode == "melimi"
    assert decision.use_melimi is True


def test_explicit_standard_request_stays_standard():
    decision = route_message("నాకు AI గురించి చెప్పు", "standard")
    assert decision.mode == "standard"
    assert decision.use_melimi is False
    assert decision.explicit is True
