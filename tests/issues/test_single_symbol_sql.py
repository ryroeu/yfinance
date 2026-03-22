"""Fetch SQL table payloads for a single symbol and print per-table results."""

from __future__ import annotations

import argparse
import json
import sys
import time
from importlib import import_module
from pathlib import Path
from typing import Any


def _load_sql_runtime() -> tuple[tuple[type[Exception], ...], tuple[str, ...], Any]:
    try:
        sql_client = import_module("yfinance.sql.client")
    except ModuleNotFoundError:
        root = Path(__file__).resolve().parents[2]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        sql_client = import_module("yfinance.sql.client")

    return sql_client.FETCH_ERRORS, sql_client.SUPPORTED_TABLES, sql_client.fetch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch all SQL table payloads for one ticker symbol.",
    )
    parser.add_argument(
        "symbol",
        help="Ticker symbol to test, e.g. AAPL",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full fetched payloads as JSON after the summary.",
    )
    return parser


def _result_summary(table: str, data: dict[str, Any], elapsed_seconds: float) -> str:
    total_fields = len(data)
    non_null_fields = sum(value is not None for value in data.values())
    return (
        f"[{table}] ok | {elapsed_seconds:.2f}s | "
        f"non-null {non_null_fields}/{total_fields}"
    )


def main(argv: list[str] | None = None) -> int:
    """Run a single-symbol fetch against each configured SQL table."""
    args = _build_parser().parse_args(argv)
    symbol = args.symbol.upper()
    fetch_errors, tables, fetch_table = _load_sql_runtime()

    print(f"Testing symbol: {symbol}")

    results: dict[str, dict[str, Any]] = {}
    had_error = False

    for table in tables:
        started = time.perf_counter()
        try:
            data = fetch_table(table, symbol)
        except fetch_errors as error:
            had_error = True
            elapsed_seconds = time.perf_counter() - started
            print(f"[{table}] error | {elapsed_seconds:.2f}s | {error}")
            results[table] = {
                "status": "error",
                "elapsed_seconds": round(elapsed_seconds, 4),
                "error": str(error),
            }
            continue

        elapsed_seconds = time.perf_counter() - started
        print(_result_summary(table, data, elapsed_seconds))
        results[table] = {
            "status": "ok",
            "elapsed_seconds": round(elapsed_seconds, 4),
            "data": data,
        }

    if args.json:
        print()
        print(json.dumps(results, indent=2, sort_keys=True, default=str))

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
