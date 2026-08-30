from app.texl_translation_intent import TranslationMode, classify_translation_intent


def test_lexical_question_does_not_copy_accusative_surface():
    result = classify_translation_intent("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?")
    assert result.mode == TranslationMode.LEXICAL_EQUIVALENT
    assert result.preserve_source_surface_role is False


def test_sentence_translation_preserves_grammatical_role():
    result = classify_translation_intent("ధన్యవాదాన్ని తెలియజేయు — మేలిమి తెలుగులో అనువదించు")
    assert result.mode == TranslationMode.GRAMMATICAL_TRANSLATION
    assert result.preserve_source_surface_role is True


def test_plain_sentence_is_not_lexical_equivalence():
    result = classify_translation_intent("ధన్యవాదాన్ని తెలియజేయు")
    assert result.mode == TranslationMode.GENERAL
    assert result.preserve_source_surface_role is True
