from app.language_policy import LanguageVariety, choose_output_variety


def test_chat_policy_defaults_to_melimi_for_telugu():
    assert choose_output_variety("వ్యవస్థ గురించి చెప్పు").output_variety == LanguageVariety.MELIMI_TELUGU


def test_chat_policy_defaults_to_melimi_for_mixed_input():
    assert choose_output_variety("system గురించి చెప్పు").output_variety == LanguageVariety.MELIMI_TELUGU


def test_chat_policy_respects_explicit_english_request():
    decision = choose_output_variety("English lo cheppu")
    assert decision.output_variety == LanguageVariety.ENGLISH
    assert decision.explicit_output
