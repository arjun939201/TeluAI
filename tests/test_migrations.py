from unittest.mock import Mock, patch

from app.migrations import _upgrade_global_learning_identity


def test_postgres_identity_column_is_left_untouched():
    conn = Mock()
    conn.dialect.name = "postgresql"
    conn.execute.return_value.scalar.return_value = "YES"

    with patch("app.migrations.inspect") as inspect_mock:
        inspect_mock.return_value.has_table.return_value = True
        _upgrade_global_learning_identity(conn)

    assert conn.execute.call_count == 1
    assert "is_identity" in str(conn.execute.call_args.args[0])


def test_non_postgres_database_is_ignored():
    conn = Mock()
    conn.dialect.name = "sqlite"

    _upgrade_global_learning_identity(conn)

    conn.execute.assert_not_called()
