from app.chat_learning import learn_from_chat


def test_rich_mt_prose_is_observation_not_bulk_vocabulary_promotion(monkeypatch):
    promoted = []

    def fake_learn_mapping(*args, **kwargs):
        promoted.append((args, kwargs))
        return True

    monkeypatch.setattr("app.chat_learning._learn_mapping", fake_learn_mapping)
    result = learn_from_chat("ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి. ఇది మేలిమి తెలుగు వాక్యము.")
    assert result["mappings"] == 0
    assert promoted == []


def test_single_mapping_is_explicit_user_teaching(monkeypatch):
    promoted = []

    def fake_learn_mapping(*args, **kwargs):
        promoted.append((args, kwargs))
        return True

    monkeypatch.setattr("app.chat_learning._learn_mapping", fake_learn_mapping)
    result = learn_from_chat("mobile = చేవీనం")
    assert result["mappings"] == 1
    assert len(promoted) == 1
    assert promoted[0][1]["authority_source"] == "explicit_user"
