"""Fetch dividend-related quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "dividends"
TABLE_LABEL = "dividends"

_COLUMNS = [
    "dividendRate", "dividendYield", "trailingAnnualDividendYield",
    "fiveYearAvgDividendYield", "payoutRatio", "lastDividendDate", "exDividendDate",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch dividend fields for a symbol from Yahoo Finance.",
)
