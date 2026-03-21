"""Fetch growth-related quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "growth"
TABLE_LABEL = "growth"

_COLUMNS = [
    "revenueGrowth", "earningsGrowth",
    "earningsQuarterlyGrowth", "epsTrailingTwelveMonths", "epsForward",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch growth fields for a symbol from Yahoo Finance.",
)
