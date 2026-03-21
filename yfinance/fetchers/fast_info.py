"""Fetch fast-info quote fields."""

from ._helpers import build_fast_info_fetcher

TABLE_NAME = "fastInfo"
TABLE_LABEL = "fast_info"

# fast_info key -> fastInfo column name (only entries that differ)
_FIELD_MAP = {
    "yearHigh": "fiftyTwoWeekHigh",
    "yearLow": "fiftyTwoWeekLow",
    "shares": "sharesOutstanding",
}

_COLUMNS = [
    "currency", "timezone", "open", "lastPrice", "lastVolume",
    "marketCap", "previousClose", "quoteType", "sharesOutstanding",
    "fiftyDayAverage", "twoHundredDayAverage", "yearChange",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "dayHigh", "dayLow",
    "threeMonthAverageVolume", "tenDayAverageVolume",
]
fetch = build_fast_info_fetcher(
    _COLUMNS,
    _FIELD_MAP,
    "Fetch fast-info fields for a symbol from Yahoo Finance.",
)
