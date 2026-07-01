from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mcaoe.models.domain import Session


SCHEMA_VERSION = 1

MIGRATIONS: dict[int, str] = {}


@dataclass(slots=True)
class SQLiteStore:
    path: Path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    capability TEXT NOT NULL DEFAULT 'web_security',
                    target TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS exports (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    exported_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
                """
            )
            connection.commit()
            self._migrate(connection)

    def _migrate(self, connection: sqlite3.Connection) -> None:
        row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = int(row[0]) if row and row[0] else 0
        for version in range(current + 1, SCHEMA_VERSION + 1):
            sql = MIGRATIONS.get(version)
            if sql:
                connection.execute(sql)
            connection.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()

    def save_session(self, session: Session) -> None:
        self.initialize()
        payload = session.model_dump(mode="json")
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT OR REPLACE INTO sessions
                   (id, name, capability, target, payload, updated_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (
                    str(session.id),
                    session.name,
                    session.capability.value,
                    session.workflow.target,
                    json.dumps(payload, indent=2),
                ),
            )
            connection.commit()

    def load_session(self, session_id: str) -> Session | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        return Session.model_validate(payload)

    def list_sessions(self) -> list[tuple[str, str, str, str]]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT id, name, capability, target FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [(str(r[0]), str(r[1]), str(r[2]), str(r[3]) if r[3] else "") for r in rows]

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

    def export_session_json(self, session_id: str) -> str | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        result: str = row[0]
        return result

    def import_session_json(self, payload: str) -> Session | None:
        self.initialize()
        try:
            data = json.loads(payload)
            session = Session.model_validate(data)
            self.save_session(session)
            return session
        except Exception:
            return None

    def save_export_record(self, export_id: str, session_id: str, fmt: str) -> None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO exports (id, session_id, format) VALUES (?, ?, ?)",
                (export_id, session_id, fmt),
            )
            connection.commit()
