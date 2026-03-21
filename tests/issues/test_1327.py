"""Regression test for issue #1327: get_earnings raises TypeError.

The original report described a TypeError raised by ``Ticker.get_earnings()``
when the earnings payload was absent or structured differently than expected.

In the refactored codebase ``Fundamentals.earnings`` is a deprecated property
that always returns ``None`` with a ``DeprecationWarning``.  ``get_earnings()``
guards with an explicit ``None`` check and exits early, so the subscript that
previously triggered the TypeError is never reached.

These tests exercise every public call-site for the earnings path without
making any network requests (the deprecated property is pure Python).
"""

import unittest
import warnings

import yfinance.client as yf


class TestIssue1327(unittest.TestCase):
    """get_earnings() and related properties must not raise TypeError."""

    def setUp(self):
        self.ticker = yf.Ticker("AAPL")

    def test_get_earnings_yearly_does_not_raise(self):
        """get_earnings() with default freq='yearly' must not raise TypeError."""
        try:
            result = self.ticker.get_earnings()
        except TypeError as exc:
            self.fail(f"get_earnings() raised TypeError: {exc}")
        self.assertIsNone(result)

    def test_get_earnings_quarterly_does_not_raise(self):
        """get_earnings(freq='quarterly') must not raise TypeError."""
        try:
            result = self.ticker.get_earnings(freq="quarterly")
        except TypeError as exc:
            self.fail(f"get_earnings(freq='quarterly') raised TypeError: {exc}")
        self.assertIsNone(result)

    def test_get_earnings_as_dict_does_not_raise(self):
        """get_earnings(as_dict=True) must not raise TypeError."""
        try:
            result = self.ticker.get_earnings(as_dict=True)
        except TypeError as exc:
            self.fail(f"get_earnings(as_dict=True) raised TypeError: {exc}")
        self.assertIsNone(result)

    def test_earnings_property_emits_deprecation_not_type_error(self):
        """ticker.earnings property access must emit DeprecationWarning, not TypeError."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                _ = self.ticker.earnings
            except TypeError as exc:
                self.fail(f"ticker.earnings raised TypeError: {exc}")

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        self.assertTrue(
            deprecation_warnings,
            "Expected at least one DeprecationWarning from ticker.earnings",
        )

    def test_quarterly_earnings_property_does_not_raise(self):
        """ticker.quarterly_earnings must not raise TypeError."""
        try:
            result = self.ticker.quarterly_earnings
        except TypeError as exc:
            self.fail(f"ticker.quarterly_earnings raised TypeError: {exc}")
        self.assertIsNone(result)
