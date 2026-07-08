from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS entity_mentions (
    entity_id INTEGER NOT NULL,
    chunk_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
"""


@dataclass
class Entity:
    id: int
    document_id: str
    name: str
    type: str
    description: str
    summary: str | None = None


@dataclass
class EntityMention:
    entity_id: int
    chunk_id: str
    document_id: str
    page_start: int
    page_end: int


class EntityStore:
    """SQLite-backed store for extracted entities and their chunk mentions."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def add_entity(self, document_id: str, name: str, type_: str, description: str) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO entities (document_id, name, type, description) VALUES (?, ?, ?, ?)",
                (document_id, name, type_, description),
            )
            conn.commit()
            return cursor.lastrowid

    def add_mentions(self, mentions: list[EntityMention]) -> None:
        if not mentions:
            return
        with closing(self._connect()) as conn:
            conn.executemany(
                "INSERT INTO entity_mentions (entity_id, chunk_id, document_id, page_start, page_end) "
                "VALUES (?, ?, ?, ?, ?)",
                [(m.entity_id, m.chunk_id, m.document_id, m.page_start, m.page_end) for m in mentions],
            )
            conn.commit()

    def set_summary(self, entity_id: int, summary: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE entities SET summary = ? WHERE id = ?", (summary, entity_id))
            conn.commit()

    def set_type(self, entity_id: int, type_: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE entities SET type = ? WHERE id = ?", (type_, entity_id))
            conn.commit()

    def get(self, entity_id: int) -> Entity | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        return Entity(**dict(row)) if row else None

    def list_by_document(self, document_id: str) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE document_id = ? ORDER BY name", (document_id,)
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def list_by_type(self, type_: str) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE type = ? ORDER BY name", (type_,)
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def list_all(self) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM entities ORDER BY type, name").fetchall()
        return [Entity(**dict(row)) for row in rows]

    def get_mentions(self, entity_id: int) -> list[EntityMention]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entity_mentions WHERE entity_id = ? ORDER BY page_start", (entity_id,)
            ).fetchall()
        return [EntityMention(**dict(row)) for row in rows]
