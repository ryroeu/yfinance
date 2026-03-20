"""SQLite-backed timezone cache helpers."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "yfinance.db"


def lookup(key: str) -> str | None:
    """Return the cached timezone value for a key, if present."""

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM timezone WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def store(key: str, value: str) -> None:
    """Store or update a timezone cache entry."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO timezone (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def delete(key: str) -> None:
    """Delete a cached timezone entry."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM timezone WHERE key = ?", (key,))


def all_entries() -> dict[str, str]:
    """Return all cached timezone entries."""

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT key, value FROM timezone").fetchall()
    return dict(rows)
