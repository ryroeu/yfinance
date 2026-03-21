"""Shared quote-field fetch helpers."""

from typing import Any, Callable, Collection, Dict, Mapping, Sequence

import yfinance as yf

Row = Dict[str, Any]
Fetcher = Callable[[str], Row]


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
