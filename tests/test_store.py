from pathlib import Path

from mcaoe.database.store import SQLiteStore
from mcaoe.models.domain import CapabilityName, Session


def test_sqlite_store_round_trips_sessions(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    session = Session(name="roundtrip", capability=CapabilityName.infrastructure)
    store.save_session(session)

    loaded = store.load_session(str(session.id))

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.name == session.name
    assert loaded.capability == session.capability
    entries = store.list_sessions()
    assert len(entries) == 1
    assert entries[0][0] == str(session.id)
    assert entries[0][1] == "roundtrip"


def test_sqlite_store_delete_session(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    session = Session(name="delete-me")
    store.save_session(session)
    assert store.session_count() == 1
    assert store.delete_session(str(session.id)) is True
    assert store.session_count() == 0


def test_sqlite_store_session_count(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    assert store.session_count() == 0
    store.save_session(Session(name="s1"))
    store.save_session(Session(name="s2"))
    assert store.session_count() == 2


def test_sqlite_store_export_session_json(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    session = Session(name="export-test", capability=CapabilityName.web_security)
    store.save_session(session)
    payload = store.export_session_json(str(session.id))
    assert payload is not None
    assert session.name in payload


def test_sqlite_store_export_session_not_found(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    assert store.export_session_json("nonexistent") is None


def test_sqlite_store_import_session_json(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    original = Session(name="import-test", capability=CapabilityName.infrastructure)
    store.save_session(original)

    payload = store.export_session_json(str(original.id))
    assert payload is not None

    imported = store.import_session_json(payload)
    assert imported is not None
    assert imported.name == "import-test"
    assert store.session_count() >= 1


def test_sqlite_store_import_invalid_json(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    assert store.import_session_json("not valid json") is None


def test_sqlite_store_schema_version_table_created(tmp_path: Path) -> None:
    import sqlite3
    store = SQLiteStore(tmp_path / "mcaoe.sqlite3")
    store.initialize()
    with sqlite3.connect(store.path) as conn:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    assert row is not None
