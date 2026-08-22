from app.melimi import word_formation


def _install_master(monkeypatch, roots=None, affixes=None):
    monkeypatch.setattr(word_formation, "language_space_version", lambda: 1)
    monkeypatch.setattr(word_formation, "language_roots", lambda: roots or {"ముప్పు": "ముప్పు"})
    monkeypatch.setattr(word_formation, "language_affixes", lambda: affixes or [{
        "form": "కాను/కాన్",
        "kind": "suffix",
        "meaning": "agent/doer",
        "applies_to": "noun",
        "status": "MASTER",
        "source": "MASTER_RULESET",
    }])
    word_formation.reload_word_formation()


def test_master_affix_derives_from_mapped_melimi_root(monkeypatch):
    _install_master(monkeypatch, {"ప్రమాదం": "ముప్పు"})

    result = word_formation.derive_word("ప్రమాదం", "కాను")

    assert result.status == "MASTER_DERIVED"
    assert result.root == "ప్రమాదం"
    assert result.melimi_root == "ముప్పు"
    assert result.word == "ముప్పుకాను"
    assert result.meaning == "agent/doer"


def test_unknown_root_is_not_fabricated(monkeypatch):
    _install_master(monkeypatch, {})

    result = word_formation.derive_word("తెలియని", "కాను")

    assert result.status == "UNKNOWN_ROOT"
    assert result.word == "తెలియని"


def test_unknown_affix_is_not_applied(monkeypatch):
    _install_master(monkeypatch, {"ప్రమాదం": "ముప్పు"}, [])

    result = word_formation.derive_word("ప్రమాదం", "తెలియని")

    assert result.status == "UNSUPPORTED_AFFIX"
    assert result.word == "ముప్పు"
