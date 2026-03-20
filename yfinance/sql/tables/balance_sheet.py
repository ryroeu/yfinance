"""SQLite helpers for balance-sheet quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "totalCash", "totalDebt", "netDebt", "totalAssets",
    "debtToEquity", "currentRatio", "quickRatio", "bookValue",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch balance-sheet fields for a symbol from Yahoo Finance.",
)
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
