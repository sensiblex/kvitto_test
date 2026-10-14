from unittest.mock import Mock

import app.database as database


def test_get_db_yields_session_and_closes_it(monkeypatch):
    session = Mock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    db_dependency = database.get_db()

    assert next(db_dependency) is session
    db_dependency.close()
    session.close.assert_called_once_with()
