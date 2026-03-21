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

from typing import Any, Mapping, Sequence

from yfinance import fetchers
from yfinance.sql import cache
from yfinance.sql._db import delete_symbols as delete_symbols_from_db
from yfinance.sql._table_runtime import populate_table, save_row

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

_TABLE_MODULES = {
    "analyst_consensus": fetchers.analyst_consensus,
    "balance_sheet": fetchers.balance_sheet,
    "company_profile": fetchers.company_profile,
    "dividends": fetchers.dividends,
    "fast_info": fetchers.fast_info,
    "growth": fetchers.growth,
    "profitability": fetchers.profitability,
    "valuation": fetchers.valuation,
}


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
    save_row(module.TABLE_NAME, symbol, data)


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
    populate_table(symbols, module.fetch, module.TABLE_NAME, module.TABLE_LABEL)


def populate_all(symbols: Sequence[str]) -> None:
    """Fetch and store data for every symbol across all tables.

    Parameters
    ----------
    symbols:
        Sequence of ticker symbols.
    """
    for module in _TABLE_MODULES.values():
        populate_table(symbols, module.fetch, module.TABLE_NAME, module.TABLE_LABEL)


def delete_symbols(symbols: Sequence[str]) -> None:
    """Delete ticker rows across all protected SQL tables via the audited workflow."""

    delete_symbols_from_db(symbols)


# ---------------------------------------------------------------------------
# Cache (re-exported for convenience)
# ---------------------------------------------------------------------------

__all__ = [
    "cache",
    "delete_symbols",
    "fetch",
    "populate",
    "populate_all",
    "save",
]
