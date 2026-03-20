"""SQLite helpers for company-profile quote fields."""

from ._helpers import build_info_fetcher, build_populator, build_saver

_COLUMNS = [
    "longName", "sector", "industry", "country",
    "city", "state", "website", "fullTimeEmployees",
]
fetch = build_info_fetcher(
    _COLUMNS,
    "Fetch company-profile fields for a symbol from Yahoo Finance.",
)
save = build_saver(
    "companyProfile",
    "Upsert company-profile data for a symbol into the local database.",
)
populate = build_populator(
    fetch,
    save,
    "company_profile",
    "Fetch and store company-profile data for each symbol provided.",
)
