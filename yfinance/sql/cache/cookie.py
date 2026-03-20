"""SQLite-backed cookie cache helpers."""

import datetime
import pickle
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "yfinance.db"


def lookup(strategy: str) -> dict | None:
    """Return a cached cookie payload and its age for a strategy."""

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT cookie_bytes, fetch_date FROM cookie WHERE strategy = ?",
            (strategy,),
        ).fetchone()
    if not row:
        return None
    cookie = pickle.loads(row[0])
    fetch_date = datetime.datetime.fromisoformat(row[1])
    return {"cookie": cookie, "age": datetime.datetime.now() - fetch_date}


def store(strategy: str, cookie) -> None:
    """Store a serialized cookie payload for a strategy."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO cookie (strategy, fetch_date, cookie_bytes) VALUES (?, ?, ?)"
            " ON CONFLICT(strategy) DO UPDATE SET"
            "  fetch_date=excluded.fetch_date,"
            "  cookie_bytes=excluded.cookie_bytes",
            (strategy, datetime.datetime.now().isoformat(), pickle.dumps(cookie)),
        )


def delete(strategy: str) -> None:
    """Delete the cached cookie for a strategy."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM cookie WHERE strategy = ?", (strategy,))
