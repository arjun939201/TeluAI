from app.melimi import lexical


def test_main_dictionary_overrides_older_runtime_root(monkeypatch):
    monkeypatch.setattr(lexical, "language_roots", lambda: {"నిర్వచనం": "పాతపలుకు"})
    monkeypatch.setattr(
        lexical.main_dictionary,
        "lookup",
        lambda root: {"standard_form": root, "melimi_form": "నిర్వల్కు"},
    )

    assert lexical.direct_lookup("నిర్వచనం =") == "నిర్వల్కు"


def test_main_dictionary_mapping_preserves_derived_voice_operation(monkeypatch):
    monkeypatch.setattr(lexical, "language_roots", lambda: {"నిర్వచనం": "పాతపలుకు"})
    monkeypatch.setattr(
        lexical.main_dictionary,
        "lookup",
        lambda root: {"standard_form": root, "melimi_form": "నిర్వల్కు"},
    )

    assert lexical.direct_lookup("నిర్వచించబడిన =") == "నిర్వల్కబడిన"
