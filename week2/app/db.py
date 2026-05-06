from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"


def ensure_data_directory_exists() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Open a new SQLite connection.

    Retained for backward compatibility. Internal callers should prefer the
    ``_connection()`` context manager below, which guarantees the connection
    is closed in a finally block. (The plain ``with sqlite3.Connection``
    context manager only commits/rolls back the active transaction; it does
    not close the connection. Without explicit close calls the app leaks an
    OS file descriptor on every database operation.)
    """
    ensure_data_directory_exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    """Open a connection, yield it, commit/rollback, then close.

    Layers two context managers:
      - the connection's own ``with`` semantics (commit on clean exit,
        rollback on exception),
      - an explicit ``close()`` in a ``finally`` block, which sqlite3 does
        not provide for free.
    """
    ensure_data_directory_exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _execute(sql: str, params: tuple = ()) -> int:
    """Run a single INSERT/UPDATE/DELETE statement.

    Returns ``cursor.lastrowid`` (meaningful for INSERTs; effectively 0 for
    UPDATE/DELETE on a fresh connection — callers that don't care can
    discard the return value).
    """
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            return int(cursor.lastrowid or 0)
    except sqlite3.Error:
        logger.exception("Database error while executing SQL: %s", sql)
        raise


def _execute_many(sql: str, params_seq: list[tuple]) -> list[int]:
    """Run the same INSERT statement once per row, all in a single transaction.

    Added beyond the prompt's three-helper list because ``insert_action_items``
    inserts N rows in one transaction. Calling ``_execute()`` N times would
    open and commit N separate transactions — a behavior change (a partial
    failure mid-batch would leave earlier rows committed, where the original
    code would roll the whole batch back). This helper preserves the original
    all-or-nothing semantics.
    """
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            ids: list[int] = []
            for params in params_seq:
                cursor.execute(sql, params)
                ids.append(int(cursor.lastrowid or 0))
            return ids
    except sqlite3.Error:
        logger.exception("Database error while executing SQL: %s", sql)
        raise


def _query_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Run a SELECT and return one row, or None if there are no matches."""
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            return cursor.fetchone()
    except sqlite3.Error:
        logger.exception("Database error while executing SQL: %s", sql)
        raise


def _query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a SELECT and return all matching rows."""
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    except sqlite3.Error:
        logger.exception("Database error while executing SQL: %s", sql)
        raise


def init_db() -> None:
    """Create tables if they don't already exist.

    Uses ``_connection()`` directly rather than ``_execute()`` because this
    is multi-statement DDL setup; the single-statement helpers don't fit
    cleanly. The exception is still caught and logged at this level.
    """
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER,
                    text TEXT NOT NULL,
                    done INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (note_id) REFERENCES notes(id)
                );
                """
            )
    except sqlite3.Error:
        logger.exception("Database error during init_db schema creation")
        raise


def insert_note(content: str) -> int:
    return _execute("INSERT INTO notes (content) VALUES (?)", (content,))


def list_notes() -> list[sqlite3.Row]:
    return _query_all("SELECT id, content, created_at FROM notes ORDER BY id DESC")


def get_note(note_id: int) -> Optional[sqlite3.Row]:
    return _query_one(
        "SELECT id, content, created_at FROM notes WHERE id = ?",
        (note_id,),
    )


def insert_action_items(items: list[str], note_id: Optional[int] = None) -> list[int]:
    return _execute_many(
        "INSERT INTO action_items (note_id, text) VALUES (?, ?)",
        [(note_id, item) for item in items],
    )


def list_action_items(note_id: Optional[int] = None) -> list[sqlite3.Row]:
    if note_id is None:
        return _query_all(
            "SELECT id, note_id, text, done, created_at FROM action_items ORDER BY id DESC"
        )
    return _query_all(
        "SELECT id, note_id, text, done, created_at FROM action_items WHERE note_id = ? ORDER BY id DESC",
        (note_id,),
    )


def mark_action_item_done(action_item_id: int, done: bool) -> None:
    _execute(
        "UPDATE action_items SET done = ? WHERE id = ?",
        (1 if done else 0, action_item_id),
    )
