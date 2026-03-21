"""Fetch balance-sheet quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "balanceSheet"
TABLE_LABEL = "balance_sheet"

_COLUMNS = [
    "totalCash", "totalDebt",
    "debtToEquity", "currentRatio", "quickRatio", "bookValue",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch balance-sheet fields for a symbol from Yahoo Finance.",
)
