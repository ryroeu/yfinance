"""Fetch valuation-related quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "valuation"
TABLE_LABEL = "valuation"

_COLUMNS = [
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "pegRatio", "trailingPegRatio", "enterpriseValue",
    "enterpriseToEbitda", "enterpriseToRevenue",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch valuation fields for a symbol from Yahoo Finance.",
)
