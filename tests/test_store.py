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
    assert store.list_sessions() == [(str(session.id), "roundtrip")]
