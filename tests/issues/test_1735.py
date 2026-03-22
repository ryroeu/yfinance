"""Regression test for issue #1735: get_news() works intermittently; why?

Original report (2025-03-20): Users observed that ``ticker.get_news()`` returned
results inconsistently — sometimes an empty list, sometimes a populated list, with
no apparent pattern.

Root causes in the old implementation:
- The old endpoint was GET-based and subject to rate-limiting and payload variance.
- No ad-filtering: ad articles mixed into results corrupted downstream processing.
- No input validation on ``tab``, so invalid values silently fell through.
- No caching: repeated calls re-hit the network on every invocation.

Resolution in this fork:
- ``get_news()`` uses a POST-based ``/xhr/ncp`` endpoint with a ``serviceKey``
  parameter, which is the canonical programmatic news API used by Yahoo Finance.
- Ad articles are filtered out deterministically (``article.get('ad', [])``) before
  results are returned.
- The ``tab`` parameter is validated upfront; invalid values raise ``ValueError``
  before any network I/O.
- Results are cached on ``self._news`` so repeated calls do not re-hit the network.
- Malformed or missing payload keys degrade gracefully to an empty list.
"""

import unittest
from unittest.mock import MagicMock

from yfinance.base import TickerBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data: dict) -> MagicMock:
    """Return a minimal mock HTTP response that satisfies parse_json_response."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.text = ""  # must NOT contain "Will be right back"
    return mock


def _make_news_payload(stream_items: list) -> dict:
    """Wrap stream items in the expected Yahoo NCP response envelope."""
    return {
        "data": {
            "tickerStream": {
                "stream": stream_items,
            }
        }
    }


def _make_ticker() -> TickerBase:
    """Return a TickerBase with a fully mocked _data layer."""
    return TickerBase("AAPL")


def _set_post_mock(ticker: TickerBase, json_data=None) -> MagicMock:
    """Attach a mocked POST method to the ticker data layer and return it."""
    post_mock = MagicMock()
    if json_data is not None:
        post_mock.return_value = _make_response(json_data)
    data_layer = getattr(ticker, "_data")
    data_layer.post = post_mock
    return post_mock


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_SAMPLE_ARTICLES = [
    {
        "id": "abc123",
        "contentType": "story",
        "content": {"title": "Apple posts record quarterly revenue"},
    },
    {
        "id": "def456",
        "contentType": "story",
        "content": {"title": "Apple faces antitrust investigation in EU"},
    },
]

_AD_ARTICLE = {
    "id": "ad001",
    "contentType": "ad",
    "ad": ["sponsored_data"],
    "content": {"title": "Sponsored: Invest smarter today"},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIssue1735GetNewsReturnType(unittest.TestCase):
    """get_news() must always return a list — never None, never raise unexpectedly."""

    def test_returns_list(self):
        """A valid response must produce a list result."""
        ticker = _make_ticker()
        _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        result = ticker.get_news()
        self.assertIsInstance(
            result, list,
            "get_news() must return a list regardless of the API response shape.",
        )

    def test_returns_articles_from_stream(self):
        """Stream items should be returned unchanged when they are valid articles."""
        ticker = _make_ticker()
        _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        result = ticker.get_news()
        self.assertEqual(len(result), len(_SAMPLE_ARTICLES))

    def test_empty_stream_returns_empty_list(self):
        """An empty stream must yield [] rather than raising."""
        ticker = _make_ticker()
        _set_post_mock(ticker, _make_news_payload([]))
        result = ticker.get_news()
        self.assertEqual(result, [])

    def test_missing_ticker_stream_key_returns_empty_list(self):
        """If 'tickerStream' is absent the result must degrade to [] gracefully."""
        ticker = _make_ticker()
        _set_post_mock(ticker, {"data": {}})
        result = ticker.get_news()
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_empty_payload_returns_empty_list(self):
        """A completely empty JSON response body must not raise."""
        ticker = _make_ticker()
        _set_post_mock(ticker, {})
        result = ticker.get_news()
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])


class TestIssue1735AdFiltering(unittest.TestCase):
    """Ad articles must be stripped from results unconditionally."""

    def test_ads_are_excluded(self):
        """Articles marked as ads must not appear in the returned list."""
        ticker = _make_ticker()
        stream = _SAMPLE_ARTICLES + [_AD_ARTICLE]
        _set_post_mock(ticker, _make_news_payload(stream))
        result = ticker.get_news()
        ids = {article["id"] for article in result}
        self.assertNotIn(
            "ad001", ids,
            "Ad articles (with a non-empty 'ad' key) must not appear in get_news() output.",
        )

    def test_non_ad_articles_are_kept(self):
        """Valid news items must remain after ad filtering."""
        ticker = _make_ticker()
        stream = _SAMPLE_ARTICLES + [_AD_ARTICLE]
        _set_post_mock(ticker, _make_news_payload(stream))
        result = ticker.get_news()
        self.assertEqual(
            len(result), len(_SAMPLE_ARTICLES),
            "All non-ad articles must be present after filtering.",
        )

    def test_all_ads_stream_returns_empty_list(self):
        """A stream containing only ad articles must produce []."""
        ticker = _make_ticker()
        stream = [_AD_ARTICLE, dict(_AD_ARTICLE, id="ad002")]
        _set_post_mock(ticker, _make_news_payload(stream))
        result = ticker.get_news()
        self.assertEqual(result, [])


class TestIssue1735TabValidation(unittest.TestCase):
    """The tab parameter must be validated before any network I/O."""

    def test_invalid_tab_raises_value_error(self):
        """Unknown tab values should raise ValueError immediately."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker)
        with self.assertRaises(ValueError):
            ticker.get_news(tab="invalid_tab")
        post_mock.assert_not_called()

    def test_invalid_tab_does_not_call_network(self):
        """Validation must short-circuit before the HTTP POST is issued."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker)
        try:
            ticker.get_news(tab="nonsense")
        except ValueError:
            pass
        post_mock.assert_not_called()

    def test_tab_news_uses_latest_news_query_ref(self):
        """The default news tab should use the latest-news query reference."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        ticker.get_news(tab="news")
        url = post_mock.call_args.args[0]
        self.assertIn("latestNews", url)

    def test_tab_all_uses_news_all_query_ref(self):
        """The all tab should use the full-news query reference."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        ticker.get_news(tab="all")
        url = post_mock.call_args.args[0]
        self.assertIn("newsAll", url)

    def test_tab_press_releases_uses_press_release_query_ref(self):
        """The press-releases tab should use the press-release query reference."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        ticker.get_news(tab="press releases")
        url = post_mock.call_args.args[0]
        self.assertIn("pressRelease", url)


class TestIssue1735CountParameter(unittest.TestCase):
    """The count parameter must be forwarded as snippetCount in the request body."""

    def test_count_sent_as_snippet_count(self):
        """The request body should forward count via serviceConfig.snippetCount."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        ticker.get_news(count=5)
        body = post_mock.call_args.kwargs["body"]
        self.assertEqual(body["serviceConfig"]["snippetCount"], 5)

    def test_ticker_sent_in_service_config(self):
        """The ticker symbol must be passed in serviceConfig.s."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        ticker.get_news()
        body = post_mock.call_args.kwargs["body"]
        self.assertIn("AAPL", body["serviceConfig"]["s"])


class TestIssue1735Caching(unittest.TestCase):
    """Results must be cached so repeated calls do not re-hit the network."""

    def test_second_call_uses_cache(self):
        """A second call should return the cached list without another POST."""
        ticker = _make_ticker()
        post_mock = _set_post_mock(ticker, _make_news_payload(_SAMPLE_ARTICLES))
        first = ticker.get_news()
        second = ticker.get_news()
        self.assertEqual(
            post_mock.call_count, 1,
            "HTTP POST must be issued exactly once; the second call must use the cache.",
        )
        self.assertIs(first, second, "Both calls must return the identical cached list object.")
