"""Entry point for yfinance SQL storage.

Usage
-----
Populate all tables for a list of symbols::

    from yfinance.sql.client import populate_all
    populate_all(["AAPL", "MSFT", "GOOG"])

Fetch a single table for a symbol::

    from yfinance.sql.client import fetch
    row = fetch("company_profile", "AAPL")

Save a single row to a table::

    from yfinance.sql.client import save
    save("dividends", "AAPL", {"dividendRate": 0.96})

Access cache helpers directly::

    from yfinance.sql.client import cache
    cache.store_cookie("basic", my_cookie)
    cache.lookup_timezone("America/New_York")
"""

import sqlite3
from typing import Any, Mapping, Sequence

from yfinance.sql import cache
from yfinance.sql._db import delete_symbols as delete_symbols_from_db
from yfinance.sql.tables import (
    analyst_consensus,
    balance_sheet,
    company_profile,
    dividends,
    fast_info,
    growth,
    profitability,
    valuation,
)
from yfinance.exceptions import YFException

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

_TABLE_MODULES = {
    "analyst_consensus": analyst_consensus,
    "balance_sheet": balance_sheet,
    "company_profile": company_profile,
    "dividends": dividends,
    "fast_info": fast_info,
    "growth": growth,
    "profitability": profitability,
    "valuation": valuation,
}

SUPPORTED_TABLES = tuple(_TABLE_MODULES)
FETCH_ERRORS = (
    sqlite3.Error,
    KeyError,
    TypeError,
    ValueError,
    RuntimeError,
    YFException,
)


def fetch(table: str, symbol: str) -> dict[str, Any]:
    """Fetch live data for *symbol* from Yahoo Finance for the given *table*.

    Parameters
    ----------
    table:
        One of the supported table names (e.g. ``"company_profile"``).
    symbol:
        Ticker symbol (e.g. ``"AAPL"``).

    Returns
    -------
    dict
        Mapping of column names to values.
    """
    module = _TABLE_MODULES[table]
    return module.fetch(symbol)


def save(table: str, symbol: str, data: Mapping[str, Any]) -> None:
    """Upsert *data* for *symbol* into the given *table*.

    Parameters
    ----------
    table:
        One of the supported table names.
    symbol:
        Ticker symbol.
    data:
        Column-value mapping to store.
    """
    module = _TABLE_MODULES[table]
    module.save(symbol, data)


def populate(table: str, symbols: Sequence[str]) -> None:
    """Fetch and store data for every symbol in *symbols* for a single *table*.

    Parameters
    ----------
    table:
        One of the supported table names.
    symbols:
        Sequence of ticker symbols.
    """
    module = _TABLE_MODULES[table]
    module.populate(symbols)


def populate_all(symbols: Sequence[str]) -> None:
    """Fetch and store data for every symbol across all tables.

    Parameters
    ----------
    symbols:
        Sequence of ticker symbols.
    """
    for module in _TABLE_MODULES.values():
        module.populate(symbols)


def delete_symbols(symbols: Sequence[str]) -> None:
    """Delete ticker rows across all protected SQL tables via the audited workflow."""

    delete_symbols_from_db(symbols)


# ---------------------------------------------------------------------------
# Cache (re-exported for convenience)
# ---------------------------------------------------------------------------

__all__ = [
    "cache",
    "delete_symbols",
    "FETCH_ERRORS",
    "fetch",
    "populate",
    "populate_all",
    "save",
    "SUPPORTED_TABLES",
]
