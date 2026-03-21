"""Compatibility wrapper for fast-info SQL table operations."""

from yfinance.fetchers import fast_info as fetcher
from yfinance.sql._table_runtime import populate_table, save_row

fetch = fetcher.fetch


def save(symbol, data):
    """Upsert fast-info data for a symbol into the local database."""

    save_row(fetcher.TABLE_NAME, symbol, data)


def populate(symbols):
    """Fetch and store fast-info data for each symbol provided."""

    populate_table(symbols, fetch, fetcher.TABLE_NAME, fetcher.TABLE_LABEL)
