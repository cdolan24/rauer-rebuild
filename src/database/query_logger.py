from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


class QueryLogger:
    """SQLite-backed log of chat queries and their response times."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def log(self, conversation_id: str, query: str, response_time_ms: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO query_log (conversation_id, query, response_time_ms, created_at) "
                "VALUES (?, ?, ?, ?)",
                (conversation_id, query, response_time_ms, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def count(self) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()
        return row[0] if row else 0
