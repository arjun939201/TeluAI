from app.melimi import language_service


def _patch_common(monkeypatch):
    monkeypatch.setattr(language_service, "language_space_version", lambda: 1)
    monkeypatch.setattr(
        language_service,
        "subject_lexicon",
        lambda: {
            "preferred": {"ప్రమాదం": "ముప్పు"},
            "registered": {"ముప్పు"},
            "forbidden": {"ప్రమాదం"},
        },
    )
    monkeypatch.setattr(language_service, "language_space_context", lambda text, max_chars: "")
    monkeypatch.setattr(language_service, "grammar_policy", lambda: "MASTER grammar")
    monkeypatch.setattr(language_service, "language_rules", lambda: [])
    monkeypatch.setattr(language_service, "language_affixes", lambda: [])


def test_generation_context_exposes_master_formations(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        language_service,
        "derive_many",
        lambda root, limit=12: [
            type("Formation", (), {
                "root": "ముప్పు",
                "affix": "కాను",
                "word": "ముప్పుకాను",
                "meaning": "agent/doer",
                "status": "MASTER_DERIVED",
            })()
        ],
    )

    context = language_service.build_generation_context("ప్రమాదం", max_chars=6000)

    assert "AUTHORIZED PRODUCTIVE FORMATIONS (MASTER ONLY)" in context
    assert "ముప్పు + కాను => მుప్పుకాను".replace("მ", "మ") in context


def test_generation_context_ignores_non_master_formations(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        language_service,
        "derive_many",
        lambda root, limit=12: [
            type("Formation", (), {
                "root": "ముప్పు",
                "affix": "నకిలీ",
                "word": "ముప్పునకిలీ",
                "meaning": "not authorized",
                "status": "PROPOSED",
            })()
        ],
    )

    context = language_service.build_generation_context("ప్రమాదం", max_chars=6000)

    assert "ముప్పునకిలీ" not in context
