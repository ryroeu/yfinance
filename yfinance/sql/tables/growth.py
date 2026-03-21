"""SQLite helpers for growth-related quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "revenueGrowth", "earningsGrowth",
    "earningsQuarterlyGrowth", "epsTrailingTwelveMonths", "epsForward",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch growth fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "growth",
    "Upsert growth data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "growth",
    "Fetch and store growth data for each symbol provided.",
)
