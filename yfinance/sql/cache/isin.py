"""SQLite-backed ISIN cache helpers."""

import datetime

from yfinance.sql._db import get_connection


def lookup(key: str) -> str | None:
    """Return the cached ISIN value for a key, if present."""

    with get_connection() as conn:
        row = conn.execute("SELECT value FROM isin WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def store(key: str, value: str) -> None:
    """Store or update an ISIN cache entry."""

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO isin (key, value, created_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET"
            "  value=excluded.value,"
            "  created_at=excluded.created_at",
            (key, value, datetime.datetime.now().isoformat()),
        )


def delete(key: str) -> None:
    """Delete a cached ISIN entry."""

    with get_connection() as conn:
        conn.execute("DELETE FROM isin WHERE key = ?", (key,))


def all_entries() -> dict[str, str]:
    """Return all cached ISIN entries."""

    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM isin").fetchall()
    return dict(rows)
