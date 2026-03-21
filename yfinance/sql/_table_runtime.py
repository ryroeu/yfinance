"""SQL persistence helpers for fetcher-backed quote-field modules."""

import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

from yfinance.exceptions import YFException
from yfinance.sql._db import get_connection

Row = dict[str, Any]
Fetcher = Callable[[str], Row]
Saver = Callable[[str, Mapping[str, Any]], None]

_FETCH_ERRORS = (sqlite3.Error, KeyError, TypeError, ValueError, YFException)
_POPULATE_BATCH_SIZE = 1000
_SHORT_BATCH_BREATHER_SECONDS = 120
_LONG_BATCH_BREATHER_SECONDS = 300
_INFO_TABLE_LABELS = (
    "analyst_consensus",
    "balance_sheet",
    "company_profile",
    "dividends",
    "growth",
    "profitability",
    "valuation",
)
_TABLE_BATCH_SIZES = {
    **{label: 25 for label in _INFO_TABLE_LABELS},
}
_TABLE_FIXED_BREATHERS = {
    **{label: 60 for label in _INFO_TABLE_LABELS},
}


def _batch_size_for_label(label: str) -> int:
    return _TABLE_BATCH_SIZES.get(label, _POPULATE_BATCH_SIZE)


def _sleep_seconds_for_batch(label: str, batch_number: int) -> int:
    fixed_breather = _TABLE_FIXED_BREATHERS.get(label)
    if fixed_breather is not None:
        return fixed_breather

    return (
        _LONG_BATCH_BREATHER_SECONDS
        if batch_number % 2 == 0
        else _SHORT_BATCH_BREATHER_SECONDS
    )


def save_row(table_name: str, symbol: str, data: Mapping[str, Any]) -> None:
    """Upsert ``data`` for ``symbol`` into ``table_name``."""

    if not data:
        return

    columns = list(data.keys())
    cols = ", ".join(columns)
    placeholders = ", ".join("?" * len(columns))
    updates = ", ".join(f"{column}=excluded.{column}" for column in columns)
    sql = f"""
        INSERT INTO {table_name} (symbol, {cols})
        VALUES (?, {placeholders})
        ON CONFLICT(symbol) DO UPDATE SET
        {updates}
    """
    with get_connection() as conn:
        conn.execute(sql, [symbol] + list(data.values()))


def populate_symbols(
    symbols: Sequence[str],
    fetch: Fetcher,
    save: Saver,
    label: str,
) -> None:
    """Fetch and store data for each symbol, logging recoverable errors."""

    total_symbols = len(symbols)
    batch_size = _batch_size_for_label(label)
    for batch_start in range(0, total_symbols, batch_size):
        batch_number = (batch_start // batch_size) + 1
        batch = symbols[batch_start : batch_start + batch_size]
        batch_end = batch_start + len(batch)

        print(
            f"[{label}] Batch {batch_number}: processing symbols "
            f"{batch_start + 1}-{batch_end} of {total_symbols}"
        )
        for symbol in batch:
            try:
                save(symbol, fetch(symbol))
            except _FETCH_ERRORS as error:
                print(f"[{label}] {symbol}: {error}")

        if batch_end < total_symbols:
            sleep_seconds = _sleep_seconds_for_batch(label, batch_number)
            print(
                f"[{label}] Batch {batch_number}: sleeping for "
                f"{sleep_seconds} seconds before next batch"
            )
            time.sleep(sleep_seconds)


def populate_table(
    symbols: Sequence[str],
    fetch: Fetcher,
    table_name: str,
    label: str,
) -> None:
    """Fetch and store rows for one fetcher-backed SQL table."""

    def save(symbol: str, data: Mapping[str, Any]) -> None:
        save_row(table_name, symbol, data)

    populate_symbols(symbols, fetch, save, label)
