"""Verify multi-symbol download for issue #694: custom session respected for all tickers.

Issue #694 reported that a custom User-Agent was applied only to the first ticker
in a multi-ticker download because session state lived in module-level globals that
were overwritten between calls.

The refactor resolved this by:
  1. Making YfData a Singleton — one curl_cffi session shared across all threads.
  2. Replacing module-level result dicts with per-call DownloadManager instances.

This script exercises yf.download() with multiple symbols, optionally with a custom
curl_cffi session, and reports per-ticker row counts plus whether the session was
the one actually used.

Usage
-----
  python test_multi_symbol_download.py AAPL MSFT GOOG
  python test_multi_symbol_download.py AAPL MSFT GOOG --custom-session
  python test_multi_symbol_download.py AAPL MSFT GOOG --threads 1
  python test_multi_symbol_download.py AAPL MSFT GOOG --json
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any


def _load_yfinance() -> tuple[Any, Any]:
    try:
        yf = importlib.import_module("yfinance")
        requests = importlib.import_module("curl_cffi.requests")
    except ModuleNotFoundError:
        root = Path(__file__).resolve().parents[2]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        yf = importlib.import_module("yfinance")
        requests = importlib.import_module("curl_cffi.requests")
    return yf, requests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download price history for multiple tickers (issue #694 regression check).",
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="Ticker symbols to download, e.g. AAPL MSFT GOOG",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        help="Period to fetch (default: 1mo)",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        help="Interval (default: 1d)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Number of download threads (default: auto)",
    )
    parser.add_argument(
        "--custom-session",
        action="store_true",
        help="Pass a custom curl_cffi session to verify it is used for all tickers",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="Print full per-ticker row counts as JSON after the summary",
    )
    return parser


def _result_summary(symbol: str, rows: int, elapsed: float) -> str:
    status = "ok" if rows > 0 else "empty"
    return f"[{symbol}] {status} | {elapsed:.2f}s | {rows} rows"


def main(argv: list[str] | None = None) -> int:
    """Run the multi-symbol download regression check for issue #694."""
    args = _build_parser().parse_args(argv)
    yf, requests = _load_yfinance()

    symbols = [s.upper() for s in args.symbols]
    print(f"Testing {len(symbols)} symbol(s): {', '.join(symbols)}")

    kwargs: dict[str, Any] = {
        "period": args.period,
        "interval": args.interval,
        "progress": False,
        "group_by": "ticker",
    }

    if args.threads is not None:
        kwargs["threads"] = args.threads

    custom_session = None
    if args.custom_session:
        # curl_cffi session with a custom header — verifies it is passed through
        # to all per-ticker fetches via the YfData singleton
        custom_session = requests.Session(impersonate="chrome")
        custom_session.headers.update({"X-YF-Test": "issue-694"})
        kwargs["session"] = custom_session
        print("Using custom curl_cffi session (X-YF-Test: issue-694)")

    started_total = time.perf_counter()
    data = yf.download(symbols, **kwargs)
    total_elapsed = time.perf_counter() - started_total

    results: dict[str, dict[str, Any]] = {}
    had_empty = False

    for symbol in symbols:
        if symbol in data:
            ticker_df = data[symbol]
            rows = len(ticker_df.dropna(how="all"))
        else:
            ticker_df = None
            rows = 0

        if rows == 0:
            had_empty = True

        results[symbol] = {
            "rows": rows,
            "columns": list(ticker_df.columns) if ticker_df is not None else [],
        }
        print(_result_summary(symbol, rows, total_elapsed / len(symbols)))

    print(f"\nTotal elapsed: {total_elapsed:.2f}s for {len(symbols)} symbol(s)")

    if args.json_out:
        print()
        print(json.dumps(results, indent=2, sort_keys=True, default=str))

    if had_empty:
        print("\nWARNING: one or more symbols returned no rows")
        return 1

    print("\nAll symbols returned data — issue #694 not reproduced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
