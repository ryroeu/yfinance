"""Fetch company-profile quote fields."""

from ._helpers import build_info_fetcher

TABLE_NAME = "companyProfile"
TABLE_LABEL = "company_profile"

_COLUMNS = [
    "longName", "sector", "industry", "country",
    "city", "state", "website", "fullTimeEmployees",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch company-profile fields for a symbol from Yahoo Finance.",
)
