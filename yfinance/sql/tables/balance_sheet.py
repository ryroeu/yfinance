"""SQLite helpers for balance-sheet quote fields."""

from typing import Any

import pandas as pd

import yfinance.client as yf

from ._helpers import build_populator, build_saver

_COLUMNS = [
    "totalCash", "totalDebt",
    "debtToEquity", "currentRatio", "quickRatio", "bookValue", "companybookValue",
]


def _extract_company_book_value(balance_sheet: pd.DataFrame) -> Any:
    if balance_sheet.empty or "StockholdersEquity" not in balance_sheet.index:
        return None

    row = balance_sheet.loc["StockholdersEquity"]
    non_null = row.dropna()
    if non_null.empty:
        return None
    return non_null.iloc[0]


def fetch(symbol: str) -> dict[str, Any]:
    """Fetch balance-sheet fields for a symbol from Yahoo Finance."""

    ticker = yf.Ticker(symbol)
    info = ticker.info
    row = {col: info.get(col) for col in _COLUMNS if col != "companybookValue"}
    statement = ticker.get_balance_sheet(pretty=False)
    if isinstance(statement, pd.DataFrame):
        row["companybookValue"] = _extract_company_book_value(statement)
    else:
        row["companybookValue"] = None
    return row


save = build_saver(
    "balanceSheet",
    "Upsert balance-sheet data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "balance_sheet",
    "Fetch and store balance-sheet data for each symbol provided.",
)
