"""Regression test for issue #1713: crash every midnight with 'No Price data found,
Symbol may be delisted'.

Original report (2023-10-18): Users running scheduled scripts observed that
``ticker.history()`` would crash every midnight with a misleading error claiming the
symbol may be delisted, even for actively-traded tickers like AAPL.

Root cause in the original implementation:
- At midnight, the computed time window for ``period='1d'`` could span only a closed-
  market period (midnight → market open has no bars), so Yahoo returned an empty chart.
- The original code propagated this as an unhandled exception with the message
  "No data found, symbol may be delisted" — which is the raw Yahoo error string — rather
  than a typed, recoverable error.
- Because the exception was unhandled rather than returning a sentinel value, any script
  calling ``history()`` in a loop or cron job would crash instead of continuing.

Resolution in this fork:
1. ``_return_error_df`` catches all Yahoo chart failures (empty result, status code,
   chart-level error) and returns ``utils.empty_df()`` by default, so the call never
   crashes unless the caller explicitly opts in via ``YfConfig.debug.raise_on_error``.
2. When ``raise_on_error=True`` the raised exception is the typed
   ``YFPricesMissingError``, giving callers a stable type to catch rather than a
   generic crash.
3. Yahoo's own "symbol may be delisted" string coming back as a chart-level error is
   caught by ``_validate_chart_data`` and routed through the same graceful path.
"""

import json
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import yfinance.client as yf
from yfinance.config import YF_CONFIG as YfConfig
from yfinance.exceptions import YFPricesMissingError

from ..close_candidates_support import call_private


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(payload: dict) -> Mock:
    response = Mock(status_code=200)
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


def _get_history(payload: dict, **kwargs) -> pd.DataFrame:
    """Fetch history for AAPL using a fully mocked HTTP layer."""
    response = _make_response(payload)
    ticker = yf.Ticker("AAPL")
    with patch.object(ticker, "_get_ticker_tz", return_value="America/New_York"):
        history = call_private(ticker, "_lazy_load_price_history")
    client = history.get_data_client()
    with (
        patch.object(client, "get", return_value=response),
        patch.object(client, "cache_get", return_value=response),
    ):
        return history.history(**kwargs)


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

# 2023-10-17 00:00:00 UTC (a regular Tuesday trading day — bar reported at midnight)
_BAR_20231017 = 1697500800

def _empty_chart_payload() -> dict:
    """Yahoo response with an empty result list — what Yahoo returns when no bars exist."""
    return {"chart": {"result": [], "error": None}}


def _chart_error_payload() -> dict:
    """Yahoo response containing the 'symbol may be delisted' chart-level error."""
    return {
        "chart": {
            "result": None,
            "error": {
                "code": "Not Found",
                "description": "No data found, symbol may be delisted",
            },
        }
    }


def _one_day_payload() -> dict:
    """Minimal valid Yahoo daily-bar payload for AAPL on 2023-10-17."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "instrumentType": "EQUITY",
                        "exchangeTimezoneName": "America/New_York",
                        "validRanges": [
                            "1d", "5d", "1mo", "3mo", "6mo", "1y",
                            "2y", "5y", "10y", "ytd", "max",
                        ],
                        "regularMarketPrice": 177.91,
                        "tradingPeriods": [
                            [
                                {
                                    "timezone": "EDT",
                                    "gmtoffset": -14400,
                                    "start": 1697534400,   # 09:30 EDT
                                    "end": 1697558400,     # 16:00 EDT
                                }
                            ]
                        ],
                    },
                    "timestamp": [_BAR_20231017],
                    "indicators": {
                        "quote": [
                            {
                                "open":   [177.00],
                                "high":   [179.80],
                                "low":    [176.50],
                                "close":  [177.91],
                                "volume": [51234567],
                            }
                        ],
                        "adjclose": [{"adjclose": [177.91]}],
                    },
                }
            ],
            "error": None,
        }
    }


# ---------------------------------------------------------------------------
# Tests: default behaviour (raise_on_error=False)
# ---------------------------------------------------------------------------

class TestIssue1713DefaultBehaviour(unittest.TestCase):
    """With default config, history() must return an empty DataFrame — never crash."""

    def setUp(self):
        self._orig = YfConfig.debug.raise_on_error
        YfConfig.debug.raise_on_error = False

    def tearDown(self):
        YfConfig.debug.raise_on_error = self._orig

    def test_empty_chart_result_returns_empty_dataframe(self):
        """Empty Yahoo chart result must produce empty DataFrame, not an exception."""
        result = _get_history(_empty_chart_payload(), period="1d", interval="1d")
        self.assertIsInstance(
            result,
            pd.DataFrame,
            "history() must return a DataFrame even when Yahoo chart result is empty.",
        )
        self.assertTrue(
            result.empty,
            "DataFrame should be empty when Yahoo returns no chart data.",
        )

    def test_yahoo_chart_error_returns_empty_dataframe(self):
        """Yahoo's 'symbol may be delisted' chart error must not crash the caller."""
        result = _get_history(_chart_error_payload(), period="1d", interval="1d")
        self.assertIsInstance(
            result,
            pd.DataFrame,
            "history() must return a DataFrame even when Yahoo returns a chart error.",
        )
        self.assertTrue(
            result.empty,
            "DataFrame should be empty when Yahoo returns a chart-level error.",
        )

    def test_valid_data_returns_dataframe_with_rows(self):
        """When Yahoo returns a valid daily bar, history() must return it correctly."""
        result = _get_history(_one_day_payload(), period="1d", interval="1d")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(
            result.empty,
            "Expected at least one row when Yahoo returns a valid daily bar.",
        )
        self.assertIn("Close", result.columns)


# ---------------------------------------------------------------------------
# Tests: raise_on_error=True (opt-in strict mode)
# ---------------------------------------------------------------------------

class TestIssue1713RaiseOnError(unittest.TestCase):
    """With raise_on_error=True, history() must raise typed YFPricesMissingError."""

    def setUp(self):
        self._orig = YfConfig.debug.raise_on_error
        YfConfig.debug.raise_on_error = True

    def tearDown(self):
        YfConfig.debug.raise_on_error = self._orig

    def test_empty_chart_raises_yfpricesmissingerror(self):
        """Empty chart result must raise YFPricesMissingError, not a generic crash."""
        with self.assertRaises(YFPricesMissingError) as ctx:
            _get_history(_empty_chart_payload(), period="1d", interval="1d")
        self.assertIn(
            "AAPL",
            str(ctx.exception),
            "Exception message should identify the ticker.",
        )

    def test_yahoo_chart_error_raises_yfpricesmissingerror(self):
        """Yahoo's 'symbol may be delisted' chart error must raise YFPricesMissingError."""
        with self.assertRaises(YFPricesMissingError):
            _get_history(_chart_error_payload(), period="1d", interval="1d")

    def test_raised_exception_is_not_generic_exception(self):
        """The raised type must be the typed YFPricesMissingError, not a bare Exception."""
        with self.assertRaises(YFPricesMissingError):
            _get_history(_empty_chart_payload(), period="1d", interval="1d")

    def test_valid_data_does_not_raise(self):
        """Valid Yahoo data must not raise even with raise_on_error=True."""
        try:
            result = _get_history(_one_day_payload(), period="1d", interval="1d")
        except YFPricesMissingError:
            self.fail("history() raised YFPricesMissingError for valid data.")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
