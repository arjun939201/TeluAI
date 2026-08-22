from app.melimi import word_formation


def test_master_affix_derives_from_master_root(monkeypatch):
    monkeypatch.setattr(word_formation, "language_space_version", lambda: 1)
    monkeypatch.setattr(word_formation, "language_roots", lambda: {"ముప్పు": "ముప్పు"})
    monkeypatch.setattr(
        word_formation,
        "language_affixes",
        lambda: [{
            "form": "కాను/కాన్",
            "kind": "suffix",
            "meaning": "agent/doer",
            "applies_to": "noun",
            "status": "MASTER",
            "source": "MASTER_RULESET",
        }],
    )
    word_formation.reload_word_formation()

    result = word_formation.derive_word("ముప్పు", "కాను")

    assert result.status == "MASTER_DERIVED"
    assert result.word == "ముప్పుకాను"
    assert result.meaning == "agent/doer"


def test_unknown_root_is_not_fabricated(monkeypatch):
    monkeypatch.setattr(word_formation, "language_space_version", lambda: 1)
    monkeypatch.setattr(word_formation, "language_roots", lambda: {})
    monkeypatch.setattr(word_formation, "language_affixes", lambda: [])
    word_formation.reload_word_formation()

    result = word_formation.derive_word("తెలియని", "కాను")

    assert result.status == "UNKNOWN_ROOT"
    assert result.word == "తెలియని"


def test_unknown_affix_is_not_applied(monkeypatch):
    monkeypatch.setattr(word_formation, "language_space_version", lambda: 1)
    monkeypatch.setattr(word_formation, "language_roots", lambda: {"ముప్పు": "ముప్పు"})
    monkeypatch.setattr(word_formation, "language_affixes", lambda: [])
    word_formation.reload_word_formation()

    result = word_formation.derive_word("ముప్పు", "తెలియని")

    assert result.status == "UNSUPPORTED_AFFIX"
    assert result.word == "ముప్పు"
