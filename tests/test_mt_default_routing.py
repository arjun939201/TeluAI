from app.chat_learning_runtime import route_request


def test_telugu_defaults_to_melimi():
    assert route_request("ఎలా ఉన్నావు?", None) == "melimi"


def test_explicit_standard_remains_available():
    assert route_request("ఎలా ఉన్నావు?", "standard") == "standard"


def test_explicit_mt_mode_is_melimi():
    assert route_request("hello", "mt") == "melimi"


def test_english_without_mode_remains_general():
    assert route_request("What is Python?", None) == "general"
