from app.language_policy import LanguageVariety, choose_output_variety, detect_input_variety


def test_mixed_telugu_input_is_supported():
    assert detect_input_variety("system గురించి చెప్పు") == LanguageVariety.MIXED_TELUGU


def test_roman_telugu_input_is_supported():
    assert detect_input_variety("naku cheppu") == LanguageVariety.ROMAN_TELUGU


def test_melimi_is_default_output():
    decision = choose_output_variety("వ్యవస్థ గురించి చెప్పు")
    assert decision.output_variety == LanguageVariety.MELIMI_TELUGU
    assert decision.explicit_output is False


def test_explicit_english_overrides_melimi_default():
    decision = choose_output_variety("Explain it in English")
    assert decision.output_variety == LanguageVariety.ENGLISH
    assert decision.explicit_output is True


def test_explicit_standard_telugu_overrides_melimi_default():
    decision = choose_output_variety("సాధారణ తెలుగులో చెప్పు")
    assert decision.output_variety == LanguageVariety.STANDARD_TELUGU
    assert decision.explicit_output is True
