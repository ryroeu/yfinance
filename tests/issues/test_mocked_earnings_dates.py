"""Mocked earnings-dates regression tests for issue-specific failures."""

import unittest
from unittest.mock import Mock, patch

import yfinance.client as yf
from yfinance.data import YfData

from ..close_candidates_support import require_dataframe, require_datetime_index


class TestIssue2261(unittest.TestCase):
    """Verify get_earnings_dates() parses HTML earnings tables deterministically.

    The original issue was CI fetch flakiness: the live test path against
    https://finance.yahoo.com/calendar/earnings could fail with a JSON-decode
    error when Yahoo returned an unexpected response. These tests replace the
    live-network dependency with deterministic mocked fixtures.
    """

    _EARNINGS_HTML = """
    <html><body>
    <table>
      <thead>
        <tr>
          <th>Symbol</th><th>Company</th><th>Earnings Date</th>
          <th>EPS Estimate</th><th>Reported EPS</th><th>Surprise (%)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>AAPL</td><td>Apple Inc</td>
          <td>January 30, 2025 at 4 PM EST</td>
          <td>2.35</td><td>2.40</td><td>2.13</td>
        </tr>
        <tr>
          <td>AAPL</td><td>Apple Inc</td>
          <td>October 28, 2025 at 4 PM EDT</td>
          <td>1.62</td><td>-</td><td>-</td>
        </tr>
      </tbody>
    </table>
    </body></html>
    """

    def _make_html_response(self, html):
        response = Mock(status_code=200)
        response.text = html
        return response

    def test_parse_earnings_dates_from_html_table(self):
        """get_earnings_dates() should parse a well-formed HTML earnings table."""
        ticker = yf.Ticker("AAPL")
        fake_response = self._make_html_response(self._EARNINGS_HTML)

        with patch.object(YfData, "cache_get", autospec=True, return_value=fake_response):
            df = require_dataframe(ticker.get_earnings_dates())

        dt_index = require_datetime_index(df.index)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("EPS Estimate", df.columns)
        self.assertIn("Reported EPS", df.columns)
        self.assertIn("Surprise(%)", df.columns)
        self.assertEqual(dt_index.name, "Earnings Date")
        self.assertIsNotNone(dt_index.tz)

    def test_parse_earnings_dates_caches_result_by_limit(self):
        """get_earnings_dates() should return the same object for repeated same-limit calls."""
        ticker = yf.Ticker("AAPL")
        fake_response = self._make_html_response(self._EARNINGS_HTML)

        with patch.object(YfData, "cache_get", autospec=True, return_value=fake_response):
            df_first = ticker.get_earnings_dates(limit=12)
            df_second = ticker.get_earnings_dates(limit=12)

        self.assertIs(df_first, df_second)

    def test_parse_earnings_dates_no_table_returns_none(self):
        """get_earnings_dates() should return None when Yahoo returns a page without a table."""
        ticker = yf.Ticker("AAPL")
        empty_response = self._make_html_response("<html><body><p>No data</p></body></html>")

        with patch.object(YfData, "cache_get", autospec=True, return_value=empty_response):
            df = ticker.get_earnings_dates()

        self.assertIsNone(df)
