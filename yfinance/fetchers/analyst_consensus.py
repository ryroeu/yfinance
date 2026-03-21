"""Fetch analyst-consensus quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "analystConsensus"
TABLE_LABEL = "analyst_consensus"

_COLUMNS = [
    "targetMeanPrice", "targetMedianPrice", "targetHighPrice",
    "targetLowPrice", "recommendationKey",
    "numberOfAnalystOpinions",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch analyst-consensus fields for a symbol from Yahoo Finance.",
)
