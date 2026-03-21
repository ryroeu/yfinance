"""Stock data viewer — fetches live data from Yahoo Finance."""

from __future__ import annotations

import sqlite3
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TABLES = (
    "fast_info",
    "analyst_consensus",
    "balance_sheet",
    "company_profile",
    "dividends",
    "growth",
    "profitability",
    "valuation",
)


def _load_sql_client():
    sql_client = import_module("yfinance.sql.client")
    yfinance_exceptions = import_module("yfinance.exceptions")
    fetch_errors = (
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        yfinance_exceptions.YFException,
    )
    return sql_client, fetch_errors


def display(symbol: str, results: dict) -> None:
    width = 60
    print()
    print("=" * width)
    print(f"  {symbol}")
    print("=" * width)

    for table, result in results.items():
        print(f"\n--- {table} ---")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            continue
        for key, value in result["data"].items():
            label = f"  {key}"
            print(f"{label:<35} {value}")

    print()


def main() -> None:
    sql_client, fetch_errors = _load_sql_client()

    while True:
        try:
            raw = input("Enter stock symbol (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if raw.lower() in {"q", "quit", "exit"}:
            break

        symbol = raw.upper()
        if not symbol:
            continue

        print(f"\nFetching data for {symbol}...")
        results = {}
        for table in TABLES:
            try:
                data = sql_client.fetch(table, symbol)
                results[table] = {"data": data}
            except fetch_errors as e:
                results[table] = {"error": str(e)}

        display(symbol, results)


if __name__ == "__main__":
    main()
