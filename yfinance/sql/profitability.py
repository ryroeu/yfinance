"""SQLite helpers for profitability-related quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "profitMargins", "grossMargins", "operatingMargins",
    "ebitdaMargins", "ebitda", "returnOnEquity", "returnOnAssets",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch profitability fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "profitability",
    "Upsert profitability data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "profitability",
    "Fetch and store profitability data for each symbol provided.",
)
