"""Compatibility wrapper for analyst-consensus SQL table operations."""

from yfinance.fetchers import analyst_consensus as fetcher
from yfinance.sql._table_runtime import populate_table, save_row

fetch = fetcher.fetch


def save(symbol, data):
    """Upsert analyst-consensus data for a symbol into the local database."""

    save_row(fetcher.TABLE_NAME, symbol, data)


def populate(symbols):
    """Fetch and store analyst-consensus data for each symbol provided."""

    populate_table(symbols, fetch, fetcher.TABLE_NAME, fetcher.TABLE_LABEL)
