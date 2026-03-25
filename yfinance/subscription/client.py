"""Subscription-oriented Yahoo Finance endpoint client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from yfinance.constants import quote_summary_valid_modules
from yfinance.exceptions import YFException

from .endpoints import (
    build_chart_url,
    build_domain_url,
    build_earnings_calendar_url,
    build_fundamentals_timeseries_url,
    build_key_statistics_url,
    build_lookup_url,
    build_market_summary_url,
    build_market_time_url,
    build_news_stream_url,
    build_options_url,
    build_predefined_screener_url,
    build_quote_response_url,
    build_quote_summary_url,
    build_search_url,
    build_screener_url,
    build_visualization_url,
)

if TYPE_CHECKING:
    from yfinance.data import YfData


class SubscriptionClient:
    """Bound helper for raw Yahoo fetches that may benefit from subscriptions."""

    def __init__(self, data: "YfData"):
        self._data = data

    @staticmethod
    def _with_optional_timeout(request_args: dict[str, Any], timeout: int | float | None):
        if timeout is not None:
            request_args["timeout"] = timeout
        return request_args

    @staticmethod
    def _normalize_modules(modules: list[str]) -> str:
        if not isinstance(modules, list):
            raise YFException(
                "Should provide a list of modules, see available modules using "
                "`valid_modules`"
            )

        module_param = ",".join(
            module for module in modules if module in quote_summary_valid_modules
        )
        if len(module_param) == 0:
            raise YFException(
                "No valid modules provided, see available modules using "
                "`valid_modules`"
            )
        return module_param

    def fetch_quote_summary(
        self,
        symbol: str,
        modules: list[str],
        *,
        timeout: int | float | None = None,
    ) -> dict[str, Any]:
        params = {
            "modules": self._normalize_modules(modules),
            "corsDomain": "finance.yahoo.com",
            "formatted": "false",
            "symbol": symbol,
        }
        return self._data.get_raw_json(
            **self._with_optional_timeout(
                {
                    "url": build_quote_summary_url(symbol),
                    "params": params,
                },
                timeout,
            )
        )

    def fetch_quote_response(
        self,
        symbol: str,
        *,
        timeout: int | float | None = None,
    ) -> dict[str, Any]:
        params = {"symbols": symbol, "formatted": "false"}
        return self._data.get_raw_json(
            **self._with_optional_timeout(
                {
                    "url": build_quote_response_url(),
                    "params": params,
                },
                timeout,
            )
        )

    def fetch_chart(
        self,
        symbol: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: int | float = 30,
        use_cache: bool = False,
    ):
        get_fn = self._data.cache_get if use_cache else self._data.get
        return get_fn(url=build_chart_url(symbol), params=params, timeout=timeout)

    def fetch_options(
        self,
        symbol: str,
        *,
        date: int | None = None,
        timeout: int | float | None = None,
    ) -> dict[str, Any]:
        return self._data.get(
            **self._with_optional_timeout(
                {"url": build_options_url(symbol, date=date)},
                timeout,
            )
        ).json()

    def fetch_fundamentals_timeseries(
        self,
        symbol: str,
        *,
        types: list[str] | None = None,
        period1: int | None = None,
        period2: int | None = None,
        query_host: str = "query2",
        timeout: int | float | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        get_fn = self._data.cache_get if use_cache else self._data.get
        response = get_fn(
            **self._with_optional_timeout(
                {
                    "url": build_fundamentals_timeseries_url(
                        symbol,
                        types=types,
                        period1=period1,
                        period2=period2,
                        query_host=query_host,
                    )
                },
                timeout,
            )
        )
        return response.json()

    def fetch_key_statistics_page(
        self,
        symbol: str,
        *,
        timeout: int | float | None = None,
    ):
        return self._data.cache_get(
            **self._with_optional_timeout(
                {"url": build_key_statistics_url(symbol)},
                timeout,
            )
        )

    def fetch_earnings_calendar_page(
        self,
        symbol: str,
        *,
        offset: int = 0,
        size: int = 25,
        timeout: int | float | None = None,
        use_cache: bool = True,
    ):
        get_fn = self._data.cache_get if use_cache else self._data.get
        return get_fn(
            **self._with_optional_timeout(
                {"url": build_earnings_calendar_url(symbol, offset, size)},
                timeout,
            )
        )

    def fetch_news_stream(
        self,
        symbol: str,
        *,
        count: int,
        query_ref: str,
        timeout: int | float | None = None,
    ):
        payload = {"serviceConfig": {"snippetCount": count, "s": [symbol]}}
        return self._data.post(
            build_news_stream_url(query_ref),
            **self._with_optional_timeout(
                {"body": payload},
                timeout,
            )
        )

    def fetch_visualization(
        self,
        body: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        timeout: int | float | None = None,
    ):
        return self._data.post(
            build_visualization_url(),
            **self._with_optional_timeout(
                {
                    "params": params,
                    "body": body,
                },
                timeout,
            )
        )

    def fetch_search(self, params, *, timeout: int | float = 30):
        return self._data.cache_get(url=build_search_url(), params=params, timeout=timeout)

    def fetch_lookup(self, params, *, timeout: int | float = 30):
        return self._data.get(url=build_lookup_url(), params=params, timeout=timeout)

    def fetch_calendar_visualization(
        self,
        body: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        timeout: int | float | None = None,
    ):
        return self.fetch_visualization(body, params=params, timeout=timeout)

    def fetch_domain(self, resource: str, *, params: dict[str, Any]) -> dict[str, Any]:
        return self._data.get_raw_json(build_domain_url(resource), params=params)

    def fetch_market_summary(self, params, *, timeout: int | float = 30):
        return self._data.cache_get(
            url=build_market_summary_url(),
            params=params,
            timeout=timeout,
        )

    def fetch_market_time(self, params, *, timeout: int | float = 30):
        return self._data.cache_get(
            url=build_market_time_url(),
            params=params,
            timeout=timeout,
        )

    def fetch_predefined_screener(self, params):
        return self._data.get(url=build_predefined_screener_url(), params=params)

    def fetch_custom_screener(self, payload: str, *, params):
        return self._data.post(build_screener_url(), data=payload, params=params)