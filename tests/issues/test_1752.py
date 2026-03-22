"""Regression test for issue #1752: replace frozendict with immutabledict.

The original report (2023-12-01) described a Gentoo Linux packaging problem:
frozendict was a C extension capped at Python 3.10 and was being removed from
the Gentoo repository.  The reporter suggested swapping it for immutabledict
(a pure-Python fork).

Our fork still uses frozendict but requires >=2.4.7, which supports modern
Python versions and is actively maintained.  The original Gentoo-specific
concern no longer applies.

These tests confirm that frozendict is importable, that its core hashability
contract holds, and that lru_cache_freezeargs (the decorator that relies on
frozendict to make dict arguments cacheable) works correctly — i.e. the
functionality the original reporter was worried about losing is intact.
"""

import unittest
from functools import lru_cache
from typing import Any, cast
from unittest.mock import MagicMock

from frozendict import frozendict

from yfinance.data import lru_cache_freezeargs
from yfinance.data import YfData


class TestFrozendictAvailability(unittest.TestCase):
    """frozendict must be importable and satisfy its core contracts."""

    def test_frozendict_is_importable(self):
        """frozendict can be imported from the frozendict package."""
        # Import already happens at module level; reaching here means success.
        self.assertTrue(callable(frozendict))

    def test_frozendict_is_hashable(self):
        """frozendict instances must be hashable so they can key an lru_cache."""
        fd = frozendict({"key": "value", "num": 42})
        try:
            h = hash(fd)
        except TypeError as exc:
            self.fail(f"frozendict is not hashable: {exc}")
        self.assertIsInstance(h, int)

    def test_frozendict_equal_dicts_have_equal_hashes(self):
        """Two frozendict instances built from the same dict must hash equally."""
        d = {"a": 1, "b": 2}
        self.assertEqual(hash(frozendict(d)), hash(frozendict(d)))

    def test_frozendict_is_immutable(self):
        """Attempts to mutate a frozendict must raise TypeError."""
        fd = frozendict({"x": 1})
        with self.assertRaises(TypeError):
            fd["x"] = 99  # type: ignore[index]

    def test_frozendict_preserves_contents(self):
        """frozendict must expose the same key/value pairs as the source dict."""
        source = {"ticker": "AAPL", "interval": "1d", "range": "1y"}
        fd = frozendict(source)
        self.assertEqual(dict(fd), source)


class TestLruCacheFreezeArgs(unittest.TestCase):
    """lru_cache_freezeargs must convert dict/list args so lru_cache can key them."""

    def setUp(self):
        self.call_count = 0

        @lru_cache_freezeargs
        @lru_cache(maxsize=8)
        def cached_fn(params):
            self.call_count += 1
            return params

        self.cached_fn = cast(Any, cached_fn)

    def test_dict_arg_does_not_raise(self):
        """Passing a plain dict must not raise a TypeError."""
        try:
            self.cached_fn({"a": 1})
        except TypeError as exc:
            self.fail(f"lru_cache_freezeargs raised TypeError for dict arg: {exc}")

    def test_identical_dict_args_hit_cache(self):
        """Calling with an equal dict twice must only invoke the underlying function once."""
        self.cached_fn({"x": 1, "y": 2})
        self.cached_fn({"x": 1, "y": 2})
        self.assertEqual(self.call_count, 1, "Cache miss on second call with identical dict")

    def test_different_dict_args_miss_cache(self):
        """Calling with different dicts must invoke the underlying function each time."""
        self.cached_fn({"x": 1})
        self.cached_fn({"x": 2})
        self.assertEqual(self.call_count, 2, "Unexpected cache hit for different dicts")

    def test_list_arg_does_not_raise(self):
        """Passing a plain list must not raise a TypeError."""
        @lru_cache_freezeargs
        @lru_cache(maxsize=8)
        def fn_with_list(items):
            return items

        try:
            cast(Any, fn_with_list)([1, 2, 3])
        except TypeError as exc:
            self.fail(f"lru_cache_freezeargs raised TypeError for list arg: {exc}")

    def test_frozen_args_are_equal_to_source(self):
        """The value returned must still compare equal to the original dict contents."""
        result = self.cached_fn({"ticker": "AAPL"})
        self.assertEqual(dict(result), {"ticker": "AAPL"})


class TestCacheGetAcceptsDictParams(unittest.TestCase):
    """YfData.cache_get must accept plain dict params without error.

    This exercises the frozendict conversion that lru_cache_freezeargs performs
    inside cache_get, which is the main call-site the original reporter was
    concerned about.
    """

    def _make_data_client(self):
        """Return a YfData instance with network I/O patched out."""
        client = cast(Any, YfData.__new__(YfData))
        # Stub out the real get() so cache_get never touches the network.
        mock_response = MagicMock()
        mock_response.status_code = 200
        client.get = MagicMock(return_value=mock_response)
        return client, mock_response

    def test_cache_get_with_dict_params_does_not_raise(self):
        """cache_get must not raise when params is a plain dict."""
        client, _ = self._make_data_client()
        try:
            client.cache_get(
                url="https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
                params={"interval": "1d", "range": "1mo"},
            )
        except TypeError as exc:
            self.fail(f"cache_get raised TypeError for dict params: {exc}")

    def test_cache_get_with_none_params_does_not_raise(self):
        """cache_get must not raise when params is None."""
        client, _ = self._make_data_client()
        try:
            client.cache_get(
                url="https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
                params=None,
            )
        except TypeError as exc:
            self.fail(f"cache_get raised TypeError for None params: {exc}")

    def test_cache_get_caches_identical_requests(self):
        """Identical url+params must result in only one call to get()."""
        client, _ = self._make_data_client()
        url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
        params = {"interval": "1d", "range": "1y"}

        client.cache_get(url=url, params=params)
        client.cache_get(url=url, params=params)

        client.get.assert_called_once()
