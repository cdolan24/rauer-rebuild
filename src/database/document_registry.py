from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    status TEXT NOT NULL,
    page_count INTEGER,
    chunk_count INTEGER,
    error_message TEXT,
    updated_at TEXT NOT NULL
);
"""


@dataclass
class DocumentRecord:
    document_id: str
    title: str
    source_path: str
    status: str  # "pending" | "processed" | "failed"
    page_count: int | None
    chunk_count: int | None
    error_message: str | None
    updated_at: str


class DocumentRegistry:
    """SQLite-backed tracker of document ingestion status."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def mark_pending(self, document_id: str, title: str, source_path: str) -> None:
        self._upsert(document_id, title, source_path, "pending", None, None, None)

    def mark_processed(self, document_id: str, title: str, source_path: str, page_count: int, chunk_count: int) -> None:
        self._upsert(document_id, title, source_path, "processed", page_count, chunk_count, None)

    def mark_failed(self, document_id: str, title: str, source_path: str, error_message: str) -> None:
        self._upsert(document_id, title, source_path, "failed", None, None, error_message)

    def _upsert(
        self,
        document_id: str,
        title: str,
        source_path: str,
        status: str,
        page_count: int | None,
        chunk_count: int | None,
        error_message: str | None,
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO documents
                    (document_id, title, source_path, status, page_count, chunk_count, error_message, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    title=excluded.title,
                    source_path=excluded.source_path,
                    status=excluded.status,
                    page_count=excluded.page_count,
                    chunk_count=excluded.chunk_count,
                    error_message=excluded.error_message,
                    updated_at=excluded.updated_at
                """,
                (
                    document_id,
                    title,
                    source_path,
                    status,
                    page_count,
                    chunk_count,
                    error_message,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get(self, document_id: str) -> DocumentRecord | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return DocumentRecord(**dict(row)) if row else None

    def list_all(self) -> list[DocumentRecord]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM documents ORDER BY updated_at DESC").fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]
