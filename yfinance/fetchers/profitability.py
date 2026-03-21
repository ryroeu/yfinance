"""Fetch profitability-related quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "profitability"
TABLE_LABEL = "profitability"

_COLUMNS = [
    "profitMargins", "grossMargins", "operatingMargins",
    "ebitdaMargins", "ebitda", "returnOnEquity", "returnOnAssets",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch profitability fields for a symbol from Yahoo Finance.",
)
