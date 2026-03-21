"""Populate or refresh tables in the yfinance SQLite database.

Usage
-----
Refresh all tables using symbols already in the DB::

    python -m yfinance.sql.populate

Refresh a single table::

    python -m yfinance.sql.populate --table fast_info

Pass an explicit symbol list::

    python -m yfinance.sql.populate --symbols AAPL MSFT GOOG

Load symbols from a CSV file (first column used as symbol source)::

    python -m yfinance.sql.populate --symbols-file path/to/symbols.csv

Combine: refresh only one table from a CSV::

    python -m yfinance.sql.populate --table valuation --symbols-file symbols.csv
"""

import argparse
import csv
import sqlite3
import sys

from yfinance.sql.client import _TABLE_MODULES, populate, populate_all
from yfinance.sql.tables._helpers import DB_PATH

_VALID_TABLES = list(_TABLE_MODULES.keys())

# ---------------------------------------------------------------------------
# Symbol helpers
# ---------------------------------------------------------------------------

def _symbols_from_db() -> list[str]:
    """Return all symbols currently stored in the database (from fastInfo)."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT symbol FROM fastInfo ORDER BY symbol").fetchall()
    return [row[0] for row in rows]


def _symbols_from_csv(path: str) -> list[str]:
    """Return symbols from the first column of a CSV file, skipping the header."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)  # skip header row
        if header is None:
            return []
        return [row[0] for row in reader if row and row[0].strip()]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m yfinance.sql.populate",
        description="Populate or refresh yfinance SQLite tables.",
    )

    symbol_group = parser.add_mutually_exclusive_group()
    symbol_group.add_argument(
        "--symbols",
        nargs="+",
        metavar="SYMBOL",
        help="One or more ticker symbols to process (e.g. AAPL MSFT).",
    )
    symbol_group.add_argument(
        "--symbols-file",
        metavar="PATH",
        help="CSV file whose first column contains ticker symbols.",
    )

    parser.add_argument(
        "--table",
        metavar="TABLE",
        choices=_VALID_TABLES,
        help=(
            f"Refresh only this table. Valid values: {', '.join(_VALID_TABLES)}. "
            "Omit to refresh all tables."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and run the populate workflow."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Resolve symbols
    if args.symbols:
        symbols = args.symbols
    elif args.symbols_file:
        symbols = _symbols_from_csv(args.symbols_file)
        if not symbols:
            print(f"No symbols found in {args.symbols_file}", file=sys.stderr)
            sys.exit(1)
    else:
        symbols = _symbols_from_db()
        if not symbols:
            print(
                "No symbols found in the database. "
                "Pass --symbols or --symbols-file to specify symbols.",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Processing {len(symbols)} symbol(s)...")

    if args.table:
        print(f"Table: {args.table}")
        populate(args.table, symbols)
    else:
        print(f"Tables: all ({', '.join(_VALID_TABLES)})")
        populate_all(symbols)

    print("Done.")


if __name__ == "__main__":
    main()
