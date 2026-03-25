"""Tests for the internal subscription Yahoo fetch client."""

import unittest
from unittest.mock import Mock

from yfinance.subscription.client import SubscriptionClient


class TestSubscriptionClient(unittest.TestCase):
    """Verify endpoint selection and request routing for subscription fetches."""

    def test_quote_summary_uses_expected_endpoint_and_params(self):
        data = Mock()
        data.get_raw_json.return_value = {"quoteSummary": {"result": []}}
        client = SubscriptionClient(data)

        client.fetch_quote_summary("AAPL", ["quoteType", "summaryDetail"])

        data.get_raw_json.assert_called_once_with(
            url="https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL",
            params={
                "modules": "quoteType,summaryDetail",
                "corsDomain": "finance.yahoo.com",
                "formatted": "false",
                "symbol": "AAPL",
            },
        )

    def test_chart_fetch_honors_cache_toggle(self):
        data = Mock()
        cached_response = object()
        data.cache_get.return_value = cached_response
        client = SubscriptionClient(data)

        response = client.fetch_chart(
            "MSFT",
            params={"range": "1d", "interval": "1d"},
            use_cache=True,
        )

        self.assertIs(response, cached_response)
        data.cache_get.assert_called_once_with(
            url="https://query2.finance.yahoo.com/v8/finance/chart/MSFT",
            params={"range": "1d", "interval": "1d"},
            timeout=30,
        )
        data.get.assert_not_called()

    def test_fundamentals_timeseries_supports_query1_host(self):
        data = Mock()
        response = Mock()
        response.json.return_value = {"timeseries": {"result": []}}
        data.cache_get.return_value = response
        client = SubscriptionClient(data)

        client.fetch_fundamentals_timeseries(
            "NVDA",
            types=["trailingPegRatio"],
            period1=1,
            period2=2,
            query_host="query1",
        )

        data.cache_get.assert_called_once_with(
            url=(
                "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/"
                "v1/finance/timeseries/NVDA?symbol=NVDA&type=trailingPegRatio"
                "&period1=1&period2=2"
            ),
        )

    def test_domain_fetch_preserves_positional_get_raw_json_contract(self):
        data = Mock()
        data.get_raw_json.return_value = {"data": {}}
        client = SubscriptionClient(data)

        client.fetch_domain(
            "sectors/technology",
            params={"formatted": "true", "region": "GB"},
        )

        data.get_raw_json.assert_called_once_with(
            "https://query1.finance.yahoo.com/v1/finance/sectors/technology",
            params={"formatted": "true", "region": "GB"},
        )

    def test_predefined_screener_fetch_uses_expected_url(self):
        data = Mock()
        client = SubscriptionClient(data)

        client.fetch_predefined_screener({"scrIds": "most_actives"})

        data.get.assert_called_once_with(
            url="https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved",
            params={"scrIds": "most_actives"},
        )

    def test_custom_screener_fetch_posts_payload(self):
        data = Mock()
        client = SubscriptionClient(data)

        client.fetch_custom_screener("{}", params={"formatted": "false"})

        data.post.assert_called_once_with(
            "https://query1.finance.yahoo.com/v1/finance/screener",
            data="{}",
            params={"formatted": "false"},
        )

    def test_calendar_visualization_posts_expected_body(self):
        data = Mock()
        client = SubscriptionClient(data)

        client.fetch_calendar_visualization(
            {"size": 5},
            params={"lang": "en-US", "region": "US"},
        )

        data.post.assert_called_once_with(
            "https://query1.finance.yahoo.com/v1/finance/visualization",
            params={"lang": "en-US", "region": "US"},
            body={"size": 5},
        )