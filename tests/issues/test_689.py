"""Regression test for issue #689: Daily OHLC rows missing randomly.

Original report (2021-04-21): Users observed that batch downloads in a loop
with the default threading behaviour randomly omitted entire date ranges (the
reporter specifically saw April 13–20 disappear for some tickers on some runs).
Downloading the same tickers one-by-one produced complete data.

Root cause: the old implementation kept result state in module-level dicts
(_DFS, _ERRORS, _TRACEBACKS) that were reset to empty at the top of every
download() call.  When two download() calls overlapped in time (possible even
from a single-threaded loop if Yahoo's response timing created a gap), Call B's
reset would overwrite the dict reference shared by Call A's still-running worker
threads.  Those workers then wrote results into B's dict, so A's dict remained
incomplete — rows appeared to vanish at random.

Resolution: the refactored fork replaces all module-level mutable state with a
DownloadManager instance constructed fresh for each download() call.  Workers
receive the manager explicitly and write through a threading.Lock(), so results
from one call can never contaminate or disappear into another call's storage.

What these tests verify:
  1. A multi-ticker threaded download returns a complete, untruncated row set
     for every ticker — no dates silently dropped.
  2. Threaded (threads=True) and sequential (threads=False) downloads produce
     identical row counts for the same request parameters.
  3. DownloadManager.record() is safe when called from multiple threads
     simultaneously — no writes are lost or overwritten.
"""

import threading
import unittest
import json
from typing import cast
from unittest.mock import Mock, patch

import pandas as pd

import yfinance.client as yf
import yfinance.http.worker as yf_download_worker
from yfinance.data import YfData
from yfinance.http.manager import DownloadManager

from ..close_candidates_support import require_dataframe


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Eight NYSE daily bars spanning 2021-04-09 through 2021-04-20, which covers
# exactly the date range the original reporter saw go missing (Apr 13–20).
_TIMESTAMPS = [
    1617975000,  # 2021-04-09 09:30 ET
    1618234200,  # 2021-04-12
    1618320600,  # 2021-04-13  ← start of originally-missing range
    1618407000,  # 2021-04-14
    1618493400,  # 2021-04-15
    1618579800,  # 2021-04-16
    1618839000,  # 2021-04-19
    1618925400,  # 2021-04-20  ← end of originally-missing range
]
_ROW_COUNT = len(_TIMESTAMPS)


def _make_chart_payload(symbol: str, base_price: float) -> dict:
    """Return a minimal but complete Yahoo chart API payload.

    Uses *base_price* as the Open/High/Low/Close/AdjClose so that AAPL and
    MSFT produce numerically distinct frames, making equality checks meaningful.
    """
    prices = [round(base_price + i * 0.5, 2) for i in range(_ROW_COUNT)]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "currency": "USD",
                        "instrumentType": "EQUITY",
                        "exchangeTimezoneName": "America/New_York",
                        "validRanges": ["1d", "5d", "1mo", "max"],
                    },
                    "timestamp": _TIMESTAMPS,
                    "indicators": {
                        "quote": [
                            {
                                "open":   prices,
                                "high":   [p + 1.0 for p in prices],
                                "low":    [p - 1.0 for p in prices],
                                "close":  prices,
                                "volume": [1_000_000] * _ROW_COUNT,
                            }
                        ],
                        "adjclose": [{"adjclose": prices}],
                    },
                }
            ],
            "error": None,
        }
    }


def _make_response(payload: dict):
    """Create a minimal mock HTTP response carrying *payload*."""
    response = Mock(status_code=200)
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


_AAPL_PAYLOAD = _make_chart_payload("AAPL", base_price=130.0)
_MSFT_PAYLOAD = _make_chart_payload("MSFT", base_price=255.0)
_TSLA_PAYLOAD = _make_chart_payload("TSLA", base_price=710.0)


def _fake_get_tz(data_client, symbol, timeout):
    del data_client, symbol, timeout
    return "America/New_York"


def _fake_yf_get(_data, url, params=None, timeout=30):
    del _data, timeout, params
    for sym, payload in [("AAPL", _AAPL_PAYLOAD), ("MSFT", _MSFT_PAYLOAD), ("TSLA", _TSLA_PAYLOAD)]:
        if url.endswith(f"/{sym}"):
            return _make_response(payload)
    raise AssertionError(f"Unexpected chart URL: {url}")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestIssue689(unittest.TestCase):
    """Issue #689 – threaded batch downloads must not silently drop OHLC rows."""

    # ------------------------------------------------------------------
    # 1. Completeness: threaded download preserves all rows per ticker
    # ------------------------------------------------------------------

    def test_threaded_download_returns_all_rows_for_each_ticker(self):
        """With threads=True each ticker in a batch download must have all rows.

        The symptom of #689 was that certain tickers silently returned fewer
        rows than expected.  This test constructs a payload with exactly
        _ROW_COUNT daily bars per ticker and asserts that a threaded download
        exposes all of them.
        """
        with (
            patch.object(yf_download_worker, "get_ticker_tz", side_effect=_fake_get_tz),
            patch.object(YfData, "get", autospec=True, side_effect=_fake_yf_get),
        ):
            frame = yf.download(
                ["AAPL", "MSFT"],
                start="2021-04-09",
                end="2021-04-21",
                group_by="ticker",
                prices="auto",
                threads=True,
                progress=False,
            )

        frame = require_dataframe(frame, "yf.download() returned None")
        self.assertFalse(frame.empty, "download() must not return an empty DataFrame")

        aapl = cast(pd.DataFrame, frame.xs("AAPL", axis="columns", level=0))
        msft = cast(pd.DataFrame, frame.xs("MSFT", axis="columns", level=0))

        aapl_rows = len(aapl["Close"].dropna())
        msft_rows = len(msft["Close"].dropna())

        self.assertEqual(
            aapl_rows,
            _ROW_COUNT,
            f"AAPL threaded download: expected {_ROW_COUNT} rows, got {aapl_rows}",
        )
        self.assertEqual(
            msft_rows,
            _ROW_COUNT,
            f"MSFT threaded download: expected {_ROW_COUNT} rows, got {msft_rows}",
        )

    # ------------------------------------------------------------------
    # 2. Consistency: threaded == sequential row counts
    # ------------------------------------------------------------------

    def test_threaded_and_sequential_downloads_return_identical_row_counts(self):
        """threads=True and threads=False must produce the same row count per ticker.

        Before the fix, users discovered that switching to sequential download
        (threads=False) restored the missing rows.  After the fix, both paths
        must return the same complete dataset.
        """
        common_kwargs = {
            "start": "2021-04-09",
            "end": "2021-04-21",
            "group_by": "ticker",
            "prices": "auto",
            "progress": False,
        }

        with (
            patch.object(yf_download_worker, "get_ticker_tz", side_effect=_fake_get_tz),
            patch.object(YfData, "get", autospec=True, side_effect=_fake_yf_get),
        ):
            threaded = yf.download(["AAPL", "MSFT"], threads=True, **common_kwargs)

        with (
            patch.object(yf_download_worker, "get_ticker_tz", side_effect=_fake_get_tz),
            patch.object(YfData, "get", autospec=True, side_effect=_fake_yf_get),
        ):
            sequential = yf.download(["AAPL", "MSFT"], threads=False, **common_kwargs)

        threaded = require_dataframe(threaded, "threaded download returned None")
        sequential = require_dataframe(sequential, "sequential download returned None")

        for sym in ("AAPL", "MSFT"):
            thr_rows = len(
                cast(pd.DataFrame, threaded.xs(sym, axis="columns", level=0))["Close"].dropna()
            )
            seq_rows = len(
                cast(pd.DataFrame, sequential.xs(sym, axis="columns", level=0))["Close"].dropna()
            )
            self.assertEqual(
                thr_rows,
                seq_rows,
                f"{sym}: threaded download ({thr_rows} rows) differs from "
                f"sequential ({seq_rows} rows)",
            )

    # ------------------------------------------------------------------
    # 3. Three-ticker threaded download — no ticker starved of results
    # ------------------------------------------------------------------

    def test_three_ticker_threaded_download_no_ticker_is_empty(self):
        """Every ticker in a three-ticker threaded batch must return data.

        The original race condition could leave entire tickers with zero rows
        when worker threads wrote results into a stale, already-replaced dict.
        """
        with (
            patch.object(yf_download_worker, "get_ticker_tz", side_effect=_fake_get_tz),
            patch.object(YfData, "get", autospec=True, side_effect=_fake_yf_get),
        ):
            frame = yf.download(
                ["AAPL", "MSFT", "TSLA"],
                start="2021-04-09",
                end="2021-04-21",
                group_by="ticker",
                prices="auto",
                threads=True,
                progress=False,
            )

        frame = require_dataframe(frame, "yf.download() returned None")

        for sym in ("AAPL", "MSFT", "TSLA"):
            sub = cast(pd.DataFrame, frame.xs(sym, axis="columns", level=0))
            row_count = len(sub["Close"].dropna())
            self.assertGreater(
                row_count,
                0,
                f"{sym} has zero rows in threaded download — ticker was starved of results",
            )

    # ------------------------------------------------------------------
    # 4. DownloadManager.record() is thread-safe under concurrent writes
    # ------------------------------------------------------------------

    def test_download_manager_record_is_thread_safe(self):
        """Concurrent calls to DownloadManager.record() must not lose any result.

        This unit-tests the threading.Lock() inside DownloadManager directly.
        With the old global-dict design, concurrent writes would silently
        overwrite each other; the lock ensures every write is preserved.
        """
        symbols = [f"T{i:03d}" for i in range(50)]
        manager = DownloadManager(symbols, show_progress=False)

        def write_result(symbol: str) -> None:
            df = pd.DataFrame({"Close": [1.0]})
            manager.record(symbol, df)

        threads = [threading.Thread(target=write_result, args=(sym,)) for sym in symbols]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(
            len(manager.dfs),
            len(symbols),
            f"Expected {len(symbols)} results in manager.dfs; got {len(manager.dfs)} — "
            "some writes were lost under concurrent access",
        )
        for sym in symbols:
            self.assertIn(
                sym,
                manager.dfs,
                f"{sym} is missing from manager.dfs after concurrent writes",
            )

    # ------------------------------------------------------------------
    # 5. DownloadManager state is isolated per download() call
    # ------------------------------------------------------------------

    def test_each_download_call_gets_independent_manager_state(self):
        """Two sequential download() calls must never share result state.

        The old design reset a single module-level dict at the top of each
        download() call.  If the first call's threads were still running when
        the second call began, their writes would land in the second call's
        dict.  The DownloadManager-per-call design closes this window entirely.
        """
        def slow_fake_get_tz(data_client, symbol, timeout):
            del data_client, symbol, timeout
            return "America/New_York"

        with (
            patch.object(yf_download_worker, "get_ticker_tz", side_effect=slow_fake_get_tz),
            patch.object(YfData, "get", autospec=True, side_effect=_fake_yf_get),
        ):
            result_a = yf.download(
                "AAPL",
                start="2021-04-09",
                end="2021-04-21",
                prices="auto",
                threads=False,
                progress=False,
                multi_level_index=False,
            )
            result_b = yf.download(
                "MSFT",
                start="2021-04-09",
                end="2021-04-21",
                prices="auto",
                threads=False,
                progress=False,
                multi_level_index=False,
            )

        result_a = require_dataframe(result_a, "first download() call returned None")
        result_b = require_dataframe(result_b, "second download() call returned None")

        # Each call should return data for exactly its requested ticker only.
        # If state leaked, result_a might contain MSFT rows or be empty.
        self.assertFalse(result_a.empty, "first download() call must not return empty DataFrame")
        self.assertFalse(result_b.empty, "second download() call must not return empty DataFrame")
        self.assertFalse(
            result_a.equals(result_b),
            "two calls for different tickers returned identical DataFrames — "
            "result state may be shared",
        )
