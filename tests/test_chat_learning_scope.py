from app.learning_scope import record_chat_learning, search_learning


def test_owner_learning_is_global_and_user_learning_is_private(tmp_path, monkeypatch):
    from app import learning_scope
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(learning_scope, "engine", engine)

    record_chat_learning(1, "owner", "సంతోషం = అలరిక")
    record_chat_learning(2, "user", "ఆనందం = ఉల్లాసం")

    user2 = search_learning("సంతోషం", 2)
    user1 = search_learning("ఆనందం", 1)

    assert any(row["scope"] == "global" and row["melimi"] == "అలరిక" for row in user2)
    assert not any(row["melimi"] == "ఉల్లాసం" for row in user1)


def test_ordinary_non_telugu_traffic_is_not_learned(monkeypatch):
    from app import learning_scope
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(learning_scope, "engine", engine)

    assert record_chat_learning(3, "user", "write a Python function") == 0
