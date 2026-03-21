"""Regression test for issue #1029.

Bug: requesting interval='30m' with period='1y' raised an error that mentioned
'15m data not available' even though the user asked for '30m'.  The internal
rewrite of 30m → 15m before the Yahoo API call was leaking into the error message.
"""

import logging
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import yfinance.client as yf

from ..close_candidates_support import call_private


def _make_error_response(error_description: str) -> Mock:
    payload = {
        "chart": {
            "result": None,
            "error": {
                "code": "Not Found",
                "description": error_description,
            },
        }
    }
    response = Mock(status_code=200)
    response.text = str(payload)
    response.json.return_value = payload
    return response


class TestIssue1029(unittest.TestCase):
    """30m interval error message must not expose the internal 15m rewrite."""

    def test_30m_error_message_does_not_mention_15m(self):
        """When 30m data is requested, the surfaced error must say '30m', not '15m'."""
        ticker = yf.Ticker("AAPL")
        history = call_private(ticker, "_lazy_load_price_history")
        client = history.get_data_client()

        yahoo_error = (
            "15m data not available for startTime=0 and endTime=9999999999. "
            "The requested range must be within the last 60 days."
        )
        response = _make_error_response(yahoo_error)

        with (
            patch.object(client, "get", return_value=response),
            patch.object(client, "cache_get", return_value=response),
            self.assertLogs(level=logging.ERROR) as log_ctx,
        ):
            result = history.history(period="1y", interval="30m")

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

        # The logged error must mention 30m (the user-requested interval), not 15m.
        full_log = "\n".join(log_ctx.output)
        self.assertIn(
            "30m",
            full_log,
            "Error log should reference the user-requested interval '30m'",
        )
        self.assertNotIn("15m", full_log, "Error log must not expose the internal 15m rewrite")

    def test_15m_error_message_preserved_for_genuine_15m_request(self):
        """A genuine 15m request should still surface '15m' in the error message."""
        ticker = yf.Ticker("AAPL")
        history = call_private(ticker, "_lazy_load_price_history")
        client = history.get_data_client()

        yahoo_error = (
            "15m data not available for startTime=0 and endTime=9999999999. "
            "The requested range must be within the last 60 days."
        )
        response = _make_error_response(yahoo_error)

        with (
            patch.object(client, "get", return_value=response),
            patch.object(client, "cache_get", return_value=response),
            self.assertLogs(level=logging.ERROR) as log_ctx,
        ):
            result = history.history(period="1y", interval="15m")

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

        full_log = "\n".join(log_ctx.output)
        self.assertIn("15m", full_log, "Error log should reference '15m' for a genuine 15m request")
