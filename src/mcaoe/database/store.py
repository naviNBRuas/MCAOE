from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from mcaoe.models.domain import Session


@dataclass(slots=True)
class SQLiteStore:
    path: Path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_session(self, session: Session) -> None:
        self.initialize()
        payload = session.model_dump(mode="json")
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO sessions (id, name, payload) VALUES (?, ?, ?)",
                (str(session.id), session.name, json.dumps(payload, indent=2)),
            )
            connection.commit()

    def load_session(self, session_id: str) -> Session | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("SELECT payload FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        return Session.model_validate(payload)

    def list_sessions(self) -> list[tuple[str, str]]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT id, name FROM sessions ORDER BY name ASC").fetchall()
        return [(str(row[0]), str(row[1])) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            connection.commit()
            return cursor.rowcount > 0

    def session_count(self) -> int:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return int(row[0]) if row else 0
