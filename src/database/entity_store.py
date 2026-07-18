from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
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

CREATE TABLE IF NOT EXISTS entity_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    related_entity_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (related_entity_id) REFERENCES entities(id)
);

CREATE TABLE IF NOT EXISTS dedupe_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keep_id INTEGER NOT NULL,
    merge_ids TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
"""

# Additive migrations applied to a database that may already exist from
# before this column/table was introduced - every prior schema change in
# this codebase was absorbed by wiping and reprocessing the database, which
# is no longer acceptable once real, expensive-to-regenerate data is in it
# (see the interactive-graph-and-merge-tools design doc). Each entry is
# tried with ALTER TABLE and the "column already exists" error is swallowed,
# so this is safe to run against both a fresh and an already-migrated db.
_COLUMN_MIGRATIONS = [
    ("entities", "merged_into_id", "INTEGER"),
    ("entity_mentions", "original_entity_id", "INTEGER"),
    ("entity_relationships", "original_entity_id", "INTEGER"),
    ("entity_relationships", "original_related_entity_id", "INTEGER"),
    ("entity_relationships", "suppressed", "INTEGER NOT NULL DEFAULT 0"),
]


@dataclass
class Entity:
    id: int
    document_id: str
    name: str
    type: str
    description: str
    summary: str | None = None
    merged_into_id: int | None = None


@dataclass
class EntityMention:
    entity_id: int
    chunk_id: str
    document_id: str
    page_start: int
    page_end: int
    original_entity_id: int | None = None


@dataclass
class Relationship:
    id: int
    entity_id: int
    related_entity_id: int
    description: str
    original_entity_id: int | None = None
    original_related_entity_id: int | None = None
    suppressed: int = 0


@dataclass
class DedupeCandidate:
    id: int
    keep_id: int
    merge_ids: list[int] = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""


class EntityStore:
    """SQLite-backed store for extracted entities and their chunk mentions."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            for table, column, definition in _COLUMN_MIGRATIONS:
                self._add_column_if_missing(conn, table, column, definition)
            conn.commit()

    @staticmethod
    def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise

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

    def merge_entities(self, keep_id: int, merge_ids: list[int]) -> None:
        """Consolidate duplicate entities onto `keep_id`: reassign all of
        their mentions and relationships, soft-delete the duplicate rows
        (set `merged_into_id` rather than deleting them), and clear
        `keep_id`'s cached summary since its mention set just changed.

        Reassigned mention/relationship rows are stamped with the id they
        were reassigned *from*, so a later `undo_merge` can move them back.
        `original_entity_id`/`original_related_entity_id` is only set if not
        already set, so a row that's part of a second, later merge keeps
        pointing at its true original entity rather than an intermediate one.
        """
        if not merge_ids:
            return
        with closing(self._connect()) as conn:
            placeholders = ",".join("?" * len(merge_ids))
            conn.execute(
                f"UPDATE entity_mentions SET "
                f"original_entity_id = COALESCE(original_entity_id, entity_id), entity_id = ? "
                f"WHERE entity_id IN ({placeholders})",
                (keep_id, *merge_ids),
            )
            conn.execute(
                f"UPDATE entity_relationships SET "
                f"original_entity_id = COALESCE(original_entity_id, entity_id), entity_id = ? "
                f"WHERE entity_id IN ({placeholders})",
                (keep_id, *merge_ids),
            )
            conn.execute(
                f"UPDATE entity_relationships SET "
                f"original_related_entity_id = COALESCE(original_related_entity_id, related_entity_id), "
                f"related_entity_id = ? WHERE related_entity_id IN ({placeholders})",
                (keep_id, *merge_ids),
            )
            # A relationship between two entities that both got merged onto
            # keep_id (or a merged entity and keep_id itself) is now a
            # self-loop - meaningless to display, so it's suppressed rather
            # than deleted, keeping its original ids so undo_merge can
            # restore it as a real relationship if the merge is reversed.
            conn.execute(
                "UPDATE entity_relationships SET suppressed = 1 WHERE entity_id = related_entity_id"
            )
            conn.execute(
                f"UPDATE entities SET merged_into_id = ? WHERE id IN ({placeholders})",
                (keep_id, *merge_ids),
            )
            conn.execute("UPDATE entities SET summary = NULL WHERE id = ?", (keep_id,))
            conn.commit()

    def can_undo_merge(self, entity_id: int) -> bool:
        """A merge is only cleanly reversible if the surviving entity hasn't
        itself been merged into something else since - otherwise the
        merged-away entity's rows are indistinguishable from the later
        merge's own rows once both live under the same further-merged id."""
        entity = self.get(entity_id)
        if entity is None or entity.merged_into_id is None:
            return False
        keeper = self.get(entity.merged_into_id)
        return keeper is not None and keeper.merged_into_id is None

    def undo_merge(self, entity_id: int) -> None:
        """Reverse a merge previously applied to `entity_id`: restore its
        entities row, move its mentions/relationships back, and re-clear the
        surviving entity's cached summary. Raises ValueError if the merge is
        not eligible for undo (see can_undo_merge)."""
        if not self.can_undo_merge(entity_id):
            raise ValueError(f"Entity {entity_id} has no merge that can be undone")
        entity = self.get(entity_id)
        keep_id = entity.merged_into_id
        with closing(self._connect()) as conn:
            conn.execute("UPDATE entities SET merged_into_id = NULL WHERE id = ?", (entity_id,))
            conn.execute(
                "UPDATE entity_mentions SET entity_id = ?, original_entity_id = NULL "
                "WHERE original_entity_id = ?",
                (entity_id, entity_id),
            )
            conn.execute(
                "UPDATE entity_relationships SET entity_id = ?, original_entity_id = NULL "
                "WHERE original_entity_id = ?",
                (entity_id, entity_id),
            )
            conn.execute(
                "UPDATE entity_relationships SET related_entity_id = ?, original_related_entity_id = NULL "
                "WHERE original_related_entity_id = ?",
                (entity_id, entity_id),
            )
            # A suppressed relationship only becomes real again once BOTH of
            # its sides have been restored to their true original entities -
            # if two entities merged into the same keep_id both had a
            # relationship to each other, undoing just one of them isn't
            # enough to make it meaningful again.
            conn.execute(
                "UPDATE entity_relationships SET suppressed = 0 "
                "WHERE suppressed = 1 AND original_entity_id IS NULL "
                "AND original_related_entity_id IS NULL AND entity_id != related_entity_id"
            )
            conn.execute("UPDATE entities SET summary = NULL WHERE id = ?", (keep_id,))
            conn.commit()

    def get(self, entity_id: int) -> Entity | None:
        """Looks up an entity regardless of merge status - unlike list_*,
        this is used for merge history/undo, which need to find a
        soft-deleted (merged-away) entity by id."""
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        return Entity(**dict(row)) if row else None

    def list_merged_away(self) -> list[Entity]:
        """Entities that have been soft-deleted by a merge - the pool that
        `can_undo_merge` filters down to what's still cleanly reversible."""
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE merged_into_id IS NOT NULL ORDER BY id DESC"
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def list_by_document(self, document_id: str) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE document_id = ? AND merged_into_id IS NULL ORDER BY name",
                (document_id,),
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def list_by_type(self, type_: str) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE type = ? AND merged_into_id IS NULL ORDER BY name", (type_,)
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def list_all(self) -> list[Entity]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE merged_into_id IS NULL ORDER BY type, name"
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def search_by_name(self, query: str, limit: int = 25) -> list[Entity]:
        """Case-insensitive substring search over active (non-merged-away)
        entity names, for the manual-merge picker - not meant for browsing
        the full store, just narrowing ~1000 entities to a pickable few."""
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE merged_into_id IS NULL AND name LIKE ? "
                "ORDER BY name LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [Entity(**dict(row)) for row in rows]

    def get_mentions(self, entity_id: int) -> list[EntityMention]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entity_mentions WHERE entity_id = ? ORDER BY page_start", (entity_id,)
            ).fetchall()
        return [EntityMention(**dict(row)) for row in rows]

    def add_relationship(self, entity_id: int, related_entity_id: int, description: str) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO entity_relationships (entity_id, related_entity_id, description) "
                "VALUES (?, ?, ?)",
                (entity_id, related_entity_id, description),
            )
            conn.commit()
            return cursor.lastrowid

    def get_relationships(self, entity_id: int) -> list[Relationship]:
        """Relationships involving `entity_id`, on either side of the stored
        row - each result's `entity_id` is normalized to the queried entity
        so callers always read `related_entity_id` as "the other one".
        Suppressed (post-merge self-loop) relationships are excluded."""
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entity_relationships WHERE (entity_id = ? OR related_entity_id = ?) "
                "AND suppressed = 0",
                (entity_id, entity_id),
            ).fetchall()
        relationships = []
        for row in rows:
            data = dict(row)
            if data["entity_id"] != entity_id:
                data["entity_id"], data["related_entity_id"] = (
                    data["related_entity_id"],
                    data["entity_id"],
                )
                data["original_entity_id"], data["original_related_entity_id"] = (
                    data["original_related_entity_id"],
                    data["original_entity_id"],
                )
            relationships.append(Relationship(**data))
        return relationships

    def list_all_relationships(self) -> list[Relationship]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM entity_relationships WHERE suppressed = 0").fetchall()
        return [Relationship(**dict(row)) for row in rows]

    def save_candidates(self, groups: list[tuple[int, list[int]]]) -> None:
        """Persist a fresh set of pending dedupe candidates, replacing any
        pending candidates left over from a previous scan - reviewed
        (approved/rejected/skipped) candidates are kept for history."""
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM dedupe_candidates WHERE status = 'pending'")
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO dedupe_candidates (keep_id, merge_ids, status, created_at) "
                "VALUES (?, ?, 'pending', ?)",
                [(keep_id, json.dumps(merge_ids), now) for keep_id, merge_ids in groups],
            )
            conn.commit()

    def list_candidates(self, status: str | None = None) -> list[DedupeCandidate]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            if status is not None:
                rows = conn.execute(
                    "SELECT * FROM dedupe_candidates WHERE status = ? ORDER BY id", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM dedupe_candidates ORDER BY id").fetchall()
        return [
            DedupeCandidate(
                id=row["id"],
                keep_id=row["keep_id"],
                merge_ids=json.loads(row["merge_ids"]),
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_candidate(self, candidate_id: int) -> DedupeCandidate | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dedupe_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
        if row is None:
            return None
        return DedupeCandidate(
            id=row["id"],
            keep_id=row["keep_id"],
            merge_ids=json.loads(row["merge_ids"]),
            status=row["status"],
            created_at=row["created_at"],
        )

    def update_candidate_status(self, candidate_id: int, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE dedupe_candidates SET status = ? WHERE id = ?", (status, candidate_id)
            )
            conn.commit()
