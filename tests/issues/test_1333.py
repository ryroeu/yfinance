"""Regression test for issue #1333: 'Adj Close' missing from history output.

The original report noted that ``yf.Ticker("MSFT").history().keys()`` omits
``Adj Close`` in both v0.1.96 and v0.2.4.

The behaviour is intentional and unchanged in this fork:

- ``auto_adjust=True`` (the default) adjusts all OHLC columns using the
  ``Adj Close / Close`` ratio and then *renames* ``Adj Close`` to ``Close``.
  The column ``Adj Close`` therefore does not appear in the output.
- ``auto_adjust=False`` leaves OHLC columns unadjusted and *preserves* the
  original ``Adj Close`` column alongside the raw ``Close``.

These tests exercise ``utils.auto_adjust`` directly so that no network
request is required.
"""

import unittest

import pandas as pd

from yfinance import utils


def _make_ohlcv_frame() -> pd.DataFrame:
    """Return a minimal OHLCV + Adj Close DataFrame for adjustment testing."""
    index = pd.date_range("2023-01-03", periods=3, freq="B", tz="America/New_York")
    return pd.DataFrame(
        {
            "Open": [130.0, 126.0, 127.0],
            "High": [133.0, 128.0, 130.0],
            "Low": [129.0, 124.0, 126.0],
            "Close": [131.0, 125.0, 129.0],
            "Adj Close": [129.5, 123.7, 128.0],
            "Volume": [1_000_000, 900_000, 1_100_000],
        },
        index=index,
    )


class TestIssue1333AdjCloseAbsentWhenAutoAdjustTrue(unittest.TestCase):
    """With auto_adjust=True (default), 'Adj Close' must not appear in output."""

    def setUp(self):
        self.raw = _make_ohlcv_frame()
        self.adjusted = utils.auto_adjust(self.raw)

    def test_adj_close_not_in_output_columns(self):
        """'Adj Close' is renamed to 'Close' and must not appear as a separate column."""
        self.assertNotIn(
            "Adj Close",
            self.adjusted.columns,
            "'Adj Close' should be absent after auto_adjust; it is renamed to 'Close'.",
        )

    def test_close_column_present_and_equals_original_adj_close(self):
        """After adjustment, 'Close' must equal the original 'Adj Close' values."""
        self.assertListEqual(
            list(self.adjusted["Close"]),
            list(self.raw["Adj Close"]),
        )

    def test_ohlcv_columns_all_present(self):
        """The adjusted frame must contain Open, High, Low, Close, and Volume."""
        required = {"Open", "High", "Low", "Close", "Volume"}
        self.assertTrue(
            required.issubset(self.adjusted.columns),
            f"Missing columns after auto_adjust: {required - set(self.adjusted.columns)}",
        )

    def test_adj_close_consumed_reduces_column_count_by_one(self):
        """auto_adjust folds 'Adj Close' into 'Close'; the output has one fewer column."""
        self.assertEqual(len(self.adjusted.columns), len(self.raw.columns) - 1)


class TestIssue1333AdjClosePresentWhenAutoAdjustFalse(unittest.TestCase):
    """With auto_adjust=False, 'Adj Close' must be preserved alongside raw Close."""

    def setUp(self):
        self.raw = _make_ohlcv_frame()

    def test_adj_close_in_raw_frame(self):
        """'Adj Close' must be present when auto_adjust has not been applied."""
        self.assertIn(
            "Adj Close",
            self.raw.columns,
            "'Adj Close' must survive when the caller opts out of auto_adjust.",
        )

    def test_close_and_adj_close_differ(self):
        """Raw Close and Adj Close must be distinct (otherwise adjustment is a no-op)."""
        self.assertFalse(
            self.raw["Close"].equals(self.raw["Adj Close"]),
            "'Close' and 'Adj Close' should differ in the raw (unadjusted) frame.",
        )
