from app.chat.router import route_message


def test_auto_telugu_is_melimi_native():
    decision = route_message("నమస్కారం")
    assert decision.mode == "melimi"
    assert decision.use_melimi is True


def test_auto_roman_telugu_is_melimi_native():
    decision = route_message("ela unnava")
    assert decision.mode == "melimi"
    assert decision.use_melimi is True


def test_auto_mixed_is_melimi_native():
    decision = route_message("ఇది Python code ఎలా పనిచేస్తుంది?")
    assert decision.mode == "melimi"
    assert decision.use_melimi is True


def test_standard_requires_explicit_opt_in():
    decision = route_message("నమస్కారం", "standard")
    assert decision.mode == "standard"
    assert decision.use_melimi is False
