"""SQLite-backed timezone cache helpers."""

from yfinance.sql._db import get_connection


def lookup(key: str) -> str | None:
    """Return the cached timezone value for a key, if present."""

    with get_connection() as conn:
        row = conn.execute("SELECT value FROM timezone WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def store(key: str, value: str) -> None:
    """Store or update a timezone cache entry."""

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO timezone (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def delete(key: str) -> None:
    """Delete a cached timezone entry."""

    with get_connection() as conn:
        conn.execute("DELETE FROM timezone WHERE key = ?", (key,))


def all_entries() -> dict[str, str]:
    """Return all cached timezone entries."""

    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM timezone").fetchall()
    return dict(rows)
