"""Endpoint builders for subscription-capable Yahoo Finance fetches."""

from __future__ import annotations

from collections.abc import Iterable

from yfinance.constants import _BASE_URL_, _QUERY1_URL_, _QUOTE_SUMMARY_URL_, _ROOT_URL_


def build_quote_summary_url(symbol: str) -> str:
    """Build the quote summary endpoint for a symbol."""
    return f"{_QUOTE_SUMMARY_URL_}/{symbol}"


def build_quote_response_url() -> str:
    """Build the quote response endpoint."""
    return f"{_QUERY1_URL_}/v7/finance/quote?"


def build_chart_url(symbol: str) -> str:
    """Build the chart endpoint for a symbol."""
    return f"{_BASE_URL_}/v8/finance/chart/{symbol}"


def build_options_url(symbol: str, date: int | None = None) -> str:
    """Build the options endpoint for a symbol and optional expiry date."""
    url = f"{_BASE_URL_}/v7/finance/options/{symbol}"
    if date is None:
        return url
    return f"{url}?date={date}"


def build_search_url() -> str:
    """Build the search endpoint."""
    return f"{_BASE_URL_}/v1/finance/search"


def build_lookup_url() -> str:
    """Build the symbol lookup endpoint."""
    return f"{_QUERY1_URL_}/v1/finance/lookup"


def build_news_stream_url(query_ref: str) -> str:
    """Build the news stream endpoint for a news query reference."""
    return f"{_ROOT_URL_}/xhr/ncp?queryRef={query_ref}&serviceKey=ncp_fin"


def build_earnings_calendar_url(symbol: str, offset: int, size: int) -> str:
    """Build the earnings calendar endpoint for a symbol."""
    return (
        f"{_ROOT_URL_}/calendar/earnings?symbol={symbol}"
        f"&offset={offset}&size={size}"
    )


def build_visualization_url() -> str:
    """Build the visualization endpoint."""
    return f"{_QUERY1_URL_}/v1/finance/visualization"


def build_key_statistics_url(symbol: str) -> str:
    """Build the key statistics page URL for a symbol."""
    return f"{_ROOT_URL_}/quote/{symbol}/key-statistics/"


def build_domain_url(resource: str) -> str:
    """Build a generic finance domain endpoint for a resource."""
    return f"{_QUERY1_URL_}/v1/finance/{resource}"


def build_market_summary_url() -> str:
    """Build the market summary endpoint."""
    return f"{_QUERY1_URL_}/v6/finance/quote/marketSummary"


def build_market_time_url() -> str:
    """Build the market time endpoint."""
    return f"{_QUERY1_URL_}/v6/finance/markettime"


def build_screener_url() -> str:
    """Build the screener endpoint."""
    return f"{_QUERY1_URL_}/v1/finance/screener"


def build_predefined_screener_url() -> str:
    """Build the saved predefined screener endpoint."""
    return f"{build_screener_url()}/predefined/saved"


def build_fundamentals_timeseries_url(
    symbol: str,
    *,
    types: Iterable[str] | None = None,
    period1: int | None = None,
    period2: int | None = None,
    query_host: str = "query2",
) -> str:
    """Build the fundamentals timeseries endpoint with optional query parameters."""
    if query_host == "query1":
        base_url = _QUERY1_URL_
    elif query_host == "query2":
        base_url = _BASE_URL_
    else:
        raise ValueError("query_host must be either 'query1' or 'query2'")

    url = f"{base_url}/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}?symbol={symbol}"
    if types:
        url += f"&type={','.join(types)}"
    if period1 is not None:
        url += f"&period1={int(period1)}"
    if period2 is not None:
        url += f"&period2={int(period2)}"
    return url
