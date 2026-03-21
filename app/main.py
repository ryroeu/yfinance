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


_MENU_OPTIONS = {
    "1": ("Show All", list(SUPPORTED_TABLES)),
    "2": ("Fast Info", ["fast_info"]),
    "3": ("Analyst Consensus", ["analyst_consensus"]),
    "4": ("Balance Sheet", ["balance_sheet"]),
    "5": ("Company Profile", ["company_profile"]),
    "6": ("Dividends", ["dividends"]),
    "7": ("Growth", ["growth"]),
    "8": ("Profitability", ["profitability"]),
    "9": ("Valuation", ["valuation"]),
}


def show_menu() -> list[str] | None:
    """Display the data menu and return the selected table list, or None to re-enter symbol."""
    print("\nWhat would you like to see?")
    for key, (label, _) in _MENU_OPTIONS.items():
        print(f"  {key}. {label}")
    print("  b. Back (enter new symbol)")
    print("  q. Quit")

    while True:
        try:
            choice = input("\nSelect an option: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if choice in _MENU_OPTIONS:
            return _MENU_OPTIONS[choice][1]
        if choice in {"b", "back"}:
            return None
        if choice in {"q", "quit", "exit"}:
            raise SystemExit(0)
        print("  Invalid choice, please try again.")


def main() -> None:
    """Run the interactive CLI for fetching stock data by symbol."""
    while True:
        try:
            raw = input("\nEnter stock symbol (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if raw.lower() in {"q", "quit", "exit"}:
            break

        symbol = raw.upper()
        if not symbol:
            continue

        while True:
            tables_to_fetch = show_menu()
            if tables_to_fetch is None:
                break

            print(f"\nFetching data for {symbol}...")
            results = {}
            for table in tables_to_fetch:
                try:
                    data = fetch(table, symbol)
                    results[table] = {"data": data}
                except FETCH_ERRORS as e:
                    results[table] = {"error": str(e)}

            display(symbol, results)

            try:
                action = input("Press Enter to return to menu, or 'b' for new symbol: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                raise SystemExit(0)

            if action in {"q", "quit", "exit"}:
                raise SystemExit(0)
            if action in {"b", "back"}:
                break


if __name__ == "__main__":
    main()
