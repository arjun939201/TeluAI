from app.melimi_language import LanguageVariety, choose_output_variety, language_contract, normalize_output_request


def test_melimi_is_default_output():
    assert choose_output_variety(None) is LanguageVariety.MELIMI
    assert choose_output_variety("") is LanguageVariety.MELIMI


def test_explicit_output_request_wins():
    assert choose_output_variety("English") is LanguageVariety.ENGLISH
    assert choose_output_variety("సాధారణ తెలుగు") is LanguageVariety.STANDARD_TELUGU
    assert choose_output_variety("melimi telugu") is LanguageVariety.MELIMI


def test_ambiguous_request_does_not_change_default():
    assert normalize_output_request("తెలుగు") is LanguageVariety.STANDARD_TELUGU
    assert choose_output_variety("తెలుగు") is LanguageVariety.STANDARD_TELUGU
    assert choose_output_variety("tell me normally") is LanguageVariety.MELIMI


def test_contract_forbids_invented_melimi_and_mechanical_replacement():
    contract = language_contract()
    assert "కల్పించవద్దు" in contract
    assert "పదాల మార్పిడిగా" in contract
    assert "అధికారిక" in contract
