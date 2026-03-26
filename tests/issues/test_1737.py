"""Regression test for issue #1737: Getting the data for revenue & earnings.

Original report (2023-11-07): The reporter wanted quarterly earnings and revenue
data matching the chart displayed on Yahoo Finance ticker pages (EPS actuals vs.
estimates, revenue bars by quarter).

The reporter discovered that `ticker.get_earnings(freq="quarterly")` raised:
    yfinance.exceptions.YFNotImplementedError:
        Have not implemented fetching 'earnings' from Yahoo API

Root cause: the old implementation had a stub that raised ``YFNotImplementedError``
instead of fetching from the ``/quoteSummary?module=earnings`` endpoint.

Resolution in this fork:
- ``ticker.earnings`` and ``ticker.quarterly_earnings`` no longer raise
  ``YFNotImplementedError``.  The ``earnings`` quoteSummary module is no longer
  available via the API, so these properties now emit a ``DeprecationWarning``
  and return ``None``.
- The actual data the reporter wanted is now served through dedicated properties:
    * ``ticker.earnings_history`` (``get_earnings_history()``) — returns a
      DataFrame indexed by quarter with columns epsEstimate, epsActual,
      epsDifference, and surprisePercent, fetched from the ``earningsHistory``
      quoteSummary module.
    * ``ticker.quarterly_income_stmt`` — provides TotalRevenue and NetIncome
      for each reported quarter.
"""

import unittest
import warnings
from unittest.mock import MagicMock, patch

import pandas as pd

from yfinance.exceptions import YFNotImplementedError
from yfinance.parsers.analysis import Analysis
from yfinance.parsers.fundamentals import Fundamentals


def _make_mock_yfdata() -> MagicMock:
    """Return a minimal YfData mock sufficient to construct scraper objects."""
    return MagicMock()


def _make_earnings_history_payload(rows: list[dict]) -> dict:
    """Wrap a list of earningsHistory row dicts in the expected quoteSummary envelope."""
    return {
        "quoteSummary": {
            "result": [
                {
                    "earningsHistory": {
                        "history": rows,
                        "maxAge": 86400,
                    }
                }
            ],
            "error": None,
        }
    }


_AAPL_HISTORY_ROWS = [
    {
        "maxAge": 1,
        "period": "+1q",
        "quarter": {"raw": 1696032000, "fmt": "2023-09-30"},
        "epsActual": {"raw": 1.46, "fmt": "1.46"},
        "epsEstimate": {"raw": 1.39, "fmt": "1.39"},
        "epsDifference": {"raw": 0.07, "fmt": "0.07"},
        "surprisePercent": {"raw": 0.0504, "fmt": "5.04%"},
    },
    {
        "maxAge": 1,
        "period": "0q",
        "quarter": {"raw": 1688083200, "fmt": "2023-06-30"},
        "epsActual": {"raw": 1.26, "fmt": "1.26"},
        "epsEstimate": {"raw": 1.19, "fmt": "1.19"},
        "epsDifference": {"raw": 0.07, "fmt": "0.07"},
        "surprisePercent": {"raw": 0.0588, "fmt": "5.88%"},
    },
]


class TestIssue1737EarningsDeprecation(unittest.TestCase):
    """ticker.earnings must not raise YFNotImplementedError; it emits a DeprecationWarning."""

    def _make_fundamentals(self) -> Fundamentals:
        return Fundamentals(_make_mock_yfdata(), "AAPL")

    def test_earnings_property_does_not_raise_yf_not_implemented_error(self):
        """Accessing Fundamentals.earnings must not raise YFNotImplementedError."""
        fundamentals = self._make_fundamentals()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                _ = fundamentals.earnings
        except YFNotImplementedError as exc:
            self.fail(
                f"Fundamentals.earnings raised YFNotImplementedError: {exc}\n"
                "Issue #1737: this should no longer raise — the property is deprecated."
            )

    def test_earnings_property_emits_deprecation_warning(self):
        """Accessing Fundamentals.earnings must emit a DeprecationWarning."""
        fundamentals = self._make_fundamentals()
        with self.assertWarns(DeprecationWarning):
            _ = fundamentals.earnings

    def test_earnings_property_returns_none(self):
        """Fundamentals.earnings must return None (endpoint no longer available)."""
        fundamentals = self._make_fundamentals()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = fundamentals.earnings
        self.assertIsNone(
            result,
            "Fundamentals.earnings should return None because the Yahoo earnings "
            "quoteSummary module is no longer available.",
        )

    def test_deprecation_warning_message_mentions_income_stmt(self):
        """The DeprecationWarning should guide users toward income_stmt."""
        fundamentals = self._make_fundamentals()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = fundamentals.earnings

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        self.assertTrue(
            deprecation_warnings,
            "Expected at least one DeprecationWarning from Fundamentals.earnings",
        )
        message = str(deprecation_warnings[0].message)
        self.assertIn(
            "income_stmt",
            message,
            "DeprecationWarning should point users to income_stmt as the replacement.",
        )


class TestIssue1737EarningsHistoryParsing(unittest.TestCase):
    """earnings_history must return a well-formed DataFrame of EPS actuals vs. estimates."""

    def _make_analysis(self) -> Analysis:
        return Analysis(_make_mock_yfdata(), "AAPL")

    def test_earnings_history_returns_dataframe(self):
        """earnings_history must return a pd.DataFrame, not raise."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIsInstance(
            result,
            pd.DataFrame,
            "earnings_history must return a pd.DataFrame.",
        )

    def test_earnings_history_index_is_datetimeindex(self):
        """earnings_history must be indexed by quarter date (DatetimeIndex)."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIsInstance(
            result.index,
            pd.DatetimeIndex,
            "earnings_history index must be a DatetimeIndex keyed by quarter.",
        )

    def test_earnings_history_row_count_matches_payload(self):
        """earnings_history must contain one row per history entry in the payload."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertEqual(
            len(result),
            len(_AAPL_HISTORY_ROWS),
            "Row count must equal the number of items in earningsHistory.history.",
        )

    def test_earnings_history_has_eps_actual_column(self):
        """earnings_history must expose epsActual — the reported EPS the reporter wanted."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIn(
            "epsActual",
            result.columns,
            "earnings_history must include epsActual (reported EPS).",
        )

    def test_earnings_history_has_eps_estimate_column(self):
        """earnings_history must expose epsEstimate — the consensus estimate."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIn(
            "epsEstimate",
            result.columns,
            "earnings_history must include epsEstimate (analyst consensus).",
        )

    def test_earnings_history_has_eps_difference_column(self):
        """earnings_history must expose epsDifference — the beat/miss magnitude."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIn(
            "epsDifference",
            result.columns,
            "earnings_history must include epsDifference.",
        )

    def test_earnings_history_has_surprise_percent_column(self):
        """earnings_history must expose surprisePercent — the beat/miss as a ratio."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIn(
            "surprisePercent",
            result.columns,
            "earnings_history must include surprisePercent.",
        )

    def test_earnings_history_eps_actual_values_are_floats(self):
        """epsActual values must be extracted from the 'raw' sub-key as floats."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        for val in result["epsActual"]:
            self.assertIsInstance(
                val,
                float,
                f"epsActual values must be floats; got {type(val).__name__}.",
            )

    def test_earnings_history_quarter_dates_are_sorted_descending(self):
        """Quarters must appear in descending chronological order (most recent first)."""
        analysis = self._make_analysis()
        # The payload has 2023-09-30 first, then 2023-06-30 — already descending.
        payload = _make_earnings_history_payload(_AAPL_HISTORY_ROWS)

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        dates = result.index.tolist()
        self.assertEqual(
            dates,
            sorted(dates, reverse=True),
            "earnings_history quarters should appear in descending date order.",
        )

    def test_earnings_history_empty_payload_returns_empty_dataframe(self):
        """When earningsHistory.history is empty, the result must be an empty DataFrame."""
        analysis = self._make_analysis()
        payload = _make_earnings_history_payload([])

        with patch.object(analysis, "_fetch", return_value=payload):
            result = analysis.earnings_history

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(
            result.empty,
            "An empty history list must produce an empty DataFrame, not raise.",
        )

    def test_earnings_history_missing_payload_returns_empty_dataframe(self):
        """When the API returns None (network failure), the result must be an empty DataFrame."""
        analysis = self._make_analysis()

        with patch.object(analysis, "_fetch", return_value=None):
            result = analysis.earnings_history

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(
            result.empty,
            "A None response from _fetch must degrade gracefully to an empty DataFrame.",
        )
