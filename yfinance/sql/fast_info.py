"""SQLite helpers for fast-info quote fields."""

from ._helpers import build_fast_info_fetcher, build_populator, build_saver

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
save = build_saver(
    "fastInfo",
    "Upsert fast-info data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "fast_info",
    "Fetch and store fast-info data for each symbol provided.",
)
