"""Stock data viewer — fetches live data from Yahoo Finance."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from yfinance.sql.client import FETCH_ERRORS, SUPPORTED_TABLES, fetch
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from yfinance.sql.client import FETCH_ERRORS, SUPPORTED_TABLES, fetch


def display(symbol: str, results: dict) -> None:
    """Print fetched table data for a symbol in a readable console layout."""
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
    """Run the interactive CLI for fetching stock data by symbol."""
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
        for table in SUPPORTED_TABLES:
            try:
                data = fetch(table, symbol)
                results[table] = {"data": data}
            except FETCH_ERRORS as e:
                results[table] = {"error": str(e)}

        display(symbol, results)


if __name__ == "__main__":
    main()
