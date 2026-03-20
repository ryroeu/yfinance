"""SQLite helpers for dividend-related quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "dividendRate", "dividendYield", "trailingAnnualDividendYield",
    "fiveYearAvgDividendYield", "payoutRatio", "lastDividendDate", "exDividendDate",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch dividend fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "dividends",
    "Upsert dividend data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "dividends",
    "Fetch and store dividend data for each symbol provided.",
)
