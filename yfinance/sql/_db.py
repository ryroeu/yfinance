"""Shared SQLite connection helpers for yfinance SQL storage."""

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

DB_PATH = Path(__file__).parent / "yfinance.db"

PROTECTED_TABLES = (
    "analystConsensus",
    "balanceSheet",
    "companyProfile",
    "dividends",
    "fastInfo",
    "growth",
    "profitability",
    "valuation",
)

_DELETE_ORDER = (
    "analystConsensus",
    "balanceSheet",
    "companyProfile",
    "dividends",
    "growth",
    "profitability",
    "valuation",
    "fastInfo",
)

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS fastInfo (
        symbol TEXT PRIMARY KEY,
        exchange TEXT,
        status TEXT,
        currency TEXT,
        timezone TEXT,
        open REAL,
        lastPrice REAL,
        lastVolume INTEGER,
        marketCap INTEGER,
        previousClose REAL,
        quoteType TEXT,
        sharesOutstanding INTEGER,
        fiftyDayAverage REAL,
        twoHundredDayAverage REAL,
        yearChange REAL,
        fiftyTwoWeekHigh REAL,
        fiftyTwoWeekLow REAL,
        dayHigh REAL,
        dayLow REAL,
        threeMonthAverageVolume INTEGER,
        tenDayAverageVolume INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analystConsensus (
        symbol TEXT PRIMARY KEY,
        targetMeanPrice REAL,
        targetMedianPrice REAL,
        targetHighPrice REAL,
        targetLowPrice REAL,
        recommendationKey TEXT,
        recommendationRating REAL,
        numberOfAnalystOpinions INTEGER,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS balanceSheet (
        symbol TEXT PRIMARY KEY,
        totalCash REAL,
        totalDebt REAL,
        netDebt REAL,
        totalAssets REAL,
        debtToEquity REAL,
        currentRatio REAL,
        quickRatio REAL,
        bookValue REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS companyProfile (
        symbol TEXT PRIMARY KEY,
        longName TEXT,
        sector TEXT,
        industry TEXT,
        country TEXT,
        city TEXT,
        state TEXT,
        website TEXT,
        fullTimeEmployees INTEGER,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dividends (
        symbol TEXT PRIMARY KEY,
        dividendRate REAL,
        dividendYield REAL,
        trailingAnnualDividendYield REAL,
        fiveYearAvgDividendYield REAL,
        payoutRatio REAL,
        lastDividendDate TEXT,
        exDividendDate TEXT,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS growth (
        symbol TEXT PRIMARY KEY,
        revenueGrowth REAL,
        revenueQuarterlyGrowth REAL,
        earningsGrowth REAL,
        earningsQuarterlyGrowth REAL,
        epsTrailingTwelveMonths REAL,
        epsForward REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profitability (
        symbol TEXT PRIMARY KEY,
        profitMargins REAL,
        grossMargins REAL,
        operatingMargins REAL,
        ebitdaMargins REAL,
        ebitda REAL,
        returnOnEquity REAL,
        returnOnAssets REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS valuation (
        symbol TEXT PRIMARY KEY,
        trailingPE REAL,
        forwardPE REAL,
        priceToBook REAL,
        priceToSalesTrailing12Months REAL,
        pegRatio REAL,
        trailingPegRatio REAL,
        enterpriseValue REAL,
        enterpriseToEbitda REAL,
        enterpriseToRevenue REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS timezone (
        key TEXT PRIMARY KEY,
        value TEXT
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS cookie (
        strategy TEXT PRIMARY KEY,
        fetch_date TEXT,
        cookie_bytes BLOB
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS isin (
        key TEXT PRIMARY KEY,
        value TEXT,
        created_at TEXT
    ) WITHOUT ROWID
    """,
)


def _trigger_sql(table_name: str) -> str:
    message = (
        f"Rows in {table_name} are protected; use "
        "yfinance.sql.delete_symbols() for audited deletes."
    )
    return f"""
    CREATE TRIGGER IF NOT EXISTS protect_delete_{table_name}
    BEFORE DELETE ON {table_name}
    BEGIN
        SELECT RAISE(
            ABORT,
            '{message}'
        )
        WHERE protected_delete_allowed() = 0;
    END
    """


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the SQLite schema and protection triggers if needed."""

    for statement in _SCHEMA_STATEMENTS:
        conn.execute(statement)
    for table_name in PROTECTED_TABLES:
        conn.execute(_trigger_sql(table_name))


def get_connection(*, allow_protected_deletes: bool = False) -> sqlite3.Connection:
    """Return a configured SQLite connection for the yfinance SQL database.

    Set ``allow_protected_deletes`` only for audited delete flows.
    """

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function(
        "protected_delete_allowed",
        0,
        lambda: 1 if allow_protected_deletes else 0,
    )
    ensure_schema(conn)
    return conn


def delete_symbols(symbols: Sequence[str]) -> None:
    """Delete all protected rows for the provided ticker symbols."""

    unique_symbols = tuple(dict.fromkeys(symbol for symbol in symbols if symbol))
    if not unique_symbols:
        return

    placeholders = ", ".join("?" for _ in unique_symbols)
    with get_connection(allow_protected_deletes=True) as conn:
        for table_name in _DELETE_ORDER:
            conn.execute(
                f"DELETE FROM {table_name} WHERE symbol IN ({placeholders})",
                unique_symbols,
            )


def protected_tables() -> Iterable[str]:
    """Return the tables whose ticker rows are protected from direct deletes."""

    return PROTECTED_TABLES
