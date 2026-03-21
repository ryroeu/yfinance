"""SQLite helpers for valuation-related quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "pegRatio", "trailingPegRatio", "enterpriseValue",
    "enterpriseToEbitda", "enterpriseToRevenue",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch valuation fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "valuation",
    "Upsert valuation data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "valuation",
    "Fetch and store valuation data for each symbol provided.",
)
