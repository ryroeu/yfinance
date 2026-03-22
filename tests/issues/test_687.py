"""Regression test for issue #687: Clarify meaning of price adjustment modes.

Original report (2021-06-07): Users were confused that `history(auto_adjust=True)`
and `history(back_adjust=True)` appeared to return identical OHLC series.

Root cause (now fixed): the old two-boolean API had four possible combinations but
only three valid states, and the default `auto_adjust=True` silently shadowed
`back_adjust=True`, making that path unreachable.

Resolution: replaced with a single `prices` parameter accepting three explicit
values — 'auto', 'back', or 'raw' — enforced by _HistoryRequest.__post_init__.

What each mode does:
    prices='auto'  ratio = AdjClose / Close
                   Replaces Open/High/Low/Close with ratio-scaled versions.
                   Output Close  = AdjClose (split + dividend adjusted).
                   'Adj Close' column is dropped.

    prices='back'  Same ratio applied to Open/High/Low.
                   Keeps the raw Close column intact.
                   'Adj Close' column is dropped.

    prices='raw'   No adjustment applied.  Returns data exactly as Yahoo
                   delivered it, including the separate 'Adj Close' column.
"""

import unittest
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pandas as pd

from yfinance import utils
from yfinance.scrapers.history.fetch import _apply_price_adjustment
from yfinance.scrapers.history.helpers import _HistoryRequest


def _make_split_frame():
    """
    Simulate two rows that span a 2:1 stock split.

    Before the split (day 0):  raw Close = 200, Adj Close = 100  (ratio = 0.5)
    After  the split (day 1):  raw Close = 100, Adj Close = 100  (ratio = 1.0)
    """
    return pd.DataFrame(
        {
            "Open":      [198.0, 99.0],
            "High":      [202.0, 101.0],
            "Low":       [196.0, 98.0],
            "Close":     [200.0, 100.0],
            "Adj Close": [100.0, 100.0],
            "Volume":    [1_000_000, 1_200_000],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
        },
        index=pd.to_datetime(["2020-08-28", "2020-08-31"]),
    )


def _numeric_array(series: pd.Series) -> np.ndarray:
    return np.asarray(series.to_numpy(dtype=float))


def _make_stub_state(prices: str) -> SimpleNamespace:
    return SimpleNamespace(prices=prices)


class TestAutoAdjustUtilFunction(unittest.TestCase):
    """utils.auto_adjust replaces OHLC with adjusted values; drops Adj Close."""

    def setUp(self):
        self.raw = _make_split_frame()
        self.adjusted = utils.auto_adjust(self.raw)

    def test_adj_close_column_is_absent(self):
        """auto_adjust must drop the 'Adj Close' column."""
        self.assertNotIn("Adj Close", self.adjusted.columns)

    def test_close_equals_original_adj_close(self):
        """After auto_adjust, Close must equal the original Adj Close."""
        np.testing.assert_array_almost_equal(
            _numeric_array(self.adjusted["Close"]),
            _numeric_array(self.raw["Adj Close"]),
        )

    def test_ohlc_are_ratio_scaled(self):
        """Open/High/Low/Close must all be scaled by AdjClose / raw Close."""
        ratios = _numeric_array(self.raw["Adj Close"] / self.raw["Close"])
        np.testing.assert_array_almost_equal(
            _numeric_array(self.adjusted["Open"]),
            _numeric_array(self.raw["Open"]) * ratios,
        )

    def test_column_order_is_preserved(self):
        """Columns present in the output must appear in the original order."""
        original_order = [c for c in self.raw.columns if c != "Adj Close"]
        self.assertEqual(list(self.adjusted.columns), original_order)


class TestBackAdjustUtilFunction(unittest.TestCase):
    """utils.back_adjust applies the same ratio to OHL but keeps raw Close."""

    def setUp(self):
        self.raw = _make_split_frame()
        self.back = utils.back_adjust(self.raw)

    def test_adj_close_column_is_absent(self):
        """back_adjust must drop 'Adj Close'."""
        self.assertNotIn("Adj Close", self.back.columns)

    def test_close_is_unchanged_raw_close(self):
        """back_adjust must NOT modify the Close column — it keeps the raw value."""
        np.testing.assert_array_almost_equal(
            _numeric_array(self.back["Close"]),
            _numeric_array(self.raw["Close"]),
        )

    def test_open_high_low_are_ratio_scaled(self):
        """Open/High/Low must be scaled by AdjClose / raw Close."""
        ratios = _numeric_array(self.raw["Adj Close"] / self.raw["Close"])
        for col in ("Open", "High", "Low"):
            with self.subTest(col=col):
                np.testing.assert_array_almost_equal(
                    _numeric_array(self.back[col]),
                    _numeric_array(self.raw[col]) * ratios,
                )


class TestAutoAdjustVsBackAdjustDiffer(unittest.TestCase):
    """The two utility functions must produce detectably different DataFrames."""

    def test_close_columns_differ(self):
        """auto_adjust Close (= AdjClose) must differ from back_adjust Close (= raw Close)
        on any row where a split or dividend creates a non-unity ratio."""
        raw = _make_split_frame()
        aa = utils.auto_adjust(raw)
        ba = utils.back_adjust(raw)

        # Day 0 has ratio 0.5; auto_adjust Close = 100, back_adjust Close = 200.
        self.assertFalse(
            np.allclose(_numeric_array(aa["Close"]), _numeric_array(ba["Close"])),
            "auto_adjust and back_adjust Close columns are unexpectedly identical — "
            "the two functions have lost their semantic distinction.",
        )

    def test_open_high_low_are_equal(self):
        """Both functions apply the same ratio to O/H/L; those columns must be equal."""
        raw = _make_split_frame()
        aa = utils.auto_adjust(raw)
        ba = utils.back_adjust(raw)

        for col in ("Open", "High", "Low"):
            with self.subTest(col=col):
                np.testing.assert_array_almost_equal(
                    _numeric_array(aa[col]),
                    _numeric_array(ba[col]),
                    err_msg=f"{col} differs between auto_adjust and back_adjust",
                )


class TestPricesParameter(unittest.TestCase):
    """Verifies the new prices= API: each mode routes to the correct path."""

    def test_prices_auto_produces_adjusted_close(self):
        """prices='auto' must replace Close with Adj Close."""
        raw = _make_split_frame()
        state = _make_stub_state("auto")
        result = _apply_price_adjustment(state, raw.copy())  # type: ignore[arg-type]

        np.testing.assert_array_almost_equal(
            _numeric_array(result["Close"]),
            _numeric_array(raw["Adj Close"]),
            err_msg="prices='auto' should set Close = Adj Close",
        )
        self.assertNotIn("Adj Close", result.columns)

    def test_prices_back_keeps_raw_close(self):
        """prices='back' must keep raw Close and adjust O/H/L only."""
        raw = _make_split_frame()
        state = _make_stub_state("back")
        result = _apply_price_adjustment(state, raw.copy())  # type: ignore[arg-type]

        np.testing.assert_array_almost_equal(
            _numeric_array(result["Close"]),
            _numeric_array(raw["Close"]),
            err_msg="prices='back' should leave Close unchanged",
        )
        self.assertNotIn("Adj Close", result.columns)

    def test_prices_raw_returns_data_unchanged(self):
        """prices='raw' must return the DataFrame exactly as received."""
        raw = _make_split_frame()
        state = _make_stub_state("raw")
        result = _apply_price_adjustment(state, raw.copy())  # type: ignore[arg-type]

        self.assertIn("Adj Close", result.columns)
        np.testing.assert_array_almost_equal(
            _numeric_array(result["Close"]),
            _numeric_array(raw["Close"]),
            err_msg="prices='raw' should not modify Close",
        )

    def test_auto_and_back_produce_different_close(self):
        """prices='auto' and prices='back' must yield different Close columns."""
        raw = _make_split_frame()
        result_auto = _apply_price_adjustment(
            _make_stub_state("auto"), raw.copy()
        )  # type: ignore[arg-type]
        result_back = _apply_price_adjustment(
            _make_stub_state("back"), raw.copy()
        )  # type: ignore[arg-type]

        self.assertFalse(
            np.allclose(
                _numeric_array(result_auto["Close"]),
                _numeric_array(result_back["Close"]),
            ),
            "prices='auto' and prices='back' must produce different Close values.",
        )

    def test_prices_invalid_value_raises(self):
        """_HistoryRequest must reject unknown prices= values."""
        with self.assertRaises(ValueError):
            _HistoryRequest(prices=cast(Any, "invalid"))

    def test_history_request_default_is_auto(self):
        """_HistoryRequest() default must be prices='auto'."""
        req = _HistoryRequest()
        self.assertEqual(req.prices, "auto")

    def test_history_request_back_is_reachable(self):
        """prices='back' must be a valid _HistoryRequest state (issue #687 fixed)."""
        req = _HistoryRequest(prices="back")
        self.assertEqual(req.prices, "back")

    def test_history_request_raw_is_reachable(self):
        """prices='raw' must be a valid _HistoryRequest state."""
        req = _HistoryRequest(prices="raw")
        self.assertEqual(req.prices, "raw")
