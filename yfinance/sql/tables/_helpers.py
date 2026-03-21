"""Shared helpers for SQLite-backed quote-field modules."""

import sqlite3
from typing import Any, Callable, Collection, Dict, Mapping, Sequence

import yfinance as yf
from yfinance.exceptions import YFException
from yfinance.sql._db import get_connection

Row = Dict[str, Any]
Fetcher = Callable[[str], Row]
Saver = Callable[[str, Mapping[str, Any]], None]

_FETCH_ERRORS = (sqlite3.Error, KeyError, TypeError, ValueError, YFException)


def fetch_info_fields(symbol: str, columns: Sequence[str]) -> Row:
    """Return selected ``Ticker.info`` fields for ``symbol``."""

    info = yf.Ticker(symbol).info
    return {col: info.get(col) for col in columns}


def fetch_fast_info_fields(
    symbol: str,
    columns: Collection[str],
    field_map: Mapping[str, str],
) -> Row:
    """Return selected ``Ticker.fast_info`` fields for ``symbol``."""

    fast_info = yf.Ticker(symbol).fast_info
    row = {}
    for key in fast_info.keys():
        column = field_map.get(key, key)
        if column in columns:
            row[column] = fast_info[key]
    return row


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

    for symbol in symbols:
        try:
            save(symbol, fetch(symbol))
        except _FETCH_ERRORS as error:
            print(f"[{label}] {symbol}: {error}")


def build_info_fetcher(columns: Sequence[str], docstring: str) -> Fetcher:
    """Create a module-specific ``Ticker.info`` fetch function."""

    def fetch(symbol: str) -> Row:
        return fetch_info_fields(symbol, columns)

    fetch.__doc__ = docstring
    return fetch


def build_fast_info_fetcher(
    columns: Collection[str],
    field_map: Mapping[str, str],
    docstring: str,
) -> Fetcher:
    """Create a module-specific ``Ticker.fast_info`` fetch function."""

    def fetch(symbol: str) -> Row:
        return fetch_fast_info_fields(symbol, columns, field_map)

    fetch.__doc__ = docstring
    return fetch


def build_saver(table_name: str, docstring: str) -> Saver:
    """Create a module-specific save function."""

    def save(symbol: str, data: Mapping[str, Any]) -> None:
        save_row(table_name, symbol, data)

    save.__doc__ = docstring
    return save


def build_populator(
    fetch: Fetcher,
    save: Saver,
    label: str,
    docstring: str,
) -> Callable[[Sequence[str]], None]:
    """Create a module-specific populate function."""

    def populate(symbols: Sequence[str]) -> None:
        populate_symbols(symbols, fetch, save, label)

    populate.__doc__ = docstring
    return populate
