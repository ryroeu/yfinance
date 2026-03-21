"""SQLite helpers for analyst-consensus quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "targetMeanPrice", "targetMedianPrice", "targetHighPrice",
    "targetLowPrice", "recommendationKey",
    "numberOfAnalystOpinions",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch analyst-consensus fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "analystConsensus",
    "Upsert analyst-consensus data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "analyst_consensus",
    "Fetch and store analyst-consensus data for each symbol provided.",
)
