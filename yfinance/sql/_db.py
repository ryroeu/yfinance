"""Shared SQLite connection helpers for yfinance SQL storage."""

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

DB_PATH = Path(__file__).parent / "yfinance.db"

_ANALYST_CONSENSUS_COLUMNS = (
    "symbol",
    "targetMeanPrice",
    "targetMedianPrice",
    "targetHighPrice",
    "targetLowPrice",
    "recommendationKey",
    "numberOfAnalystOpinions",
)

_BALANCE_SHEET_COLUMNS = (
    "symbol",
    "totalCash",
    "totalDebt",
    "debtToEquity",
    "currentRatio",
    "quickRatio",
    "bookValue",
    "companybookValue",
)

_GROWTH_COLUMNS = (
    "symbol",
    "revenueGrowth",
    "earningsGrowth",
    "earningsQuarterlyGrowth",
    "epsTrailingTwelveMonths",
    "epsForward",
)

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

_ANALYST_CONSENSUS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS analystConsensus (
        symbol TEXT PRIMARY KEY,
        targetMeanPrice REAL,
        targetMedianPrice REAL,
        targetHighPrice REAL,
        targetLowPrice REAL,
        recommendationKey TEXT,
        numberOfAnalystOpinions INTEGER,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
"""

_BALANCE_SHEET_SCHEMA = """
    CREATE TABLE IF NOT EXISTS balanceSheet (
        symbol TEXT PRIMARY KEY,
        totalCash REAL,
        totalDebt REAL,
        debtToEquity REAL,
        currentRatio REAL,
        quickRatio REAL,
        bookValue REAL,
        companybookValue REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
"""

_GROWTH_SCHEMA = """
    CREATE TABLE IF NOT EXISTS growth (
        symbol TEXT PRIMARY KEY,
        revenueGrowth REAL,
        earningsGrowth REAL,
        earningsQuarterlyGrowth REAL,
        epsTrailingTwelveMonths REAL,
        epsForward REAL,
        FOREIGN KEY (symbol) REFERENCES fastInfo(symbol)
    )
"""

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
    _ANALYST_CONSENSUS_SCHEMA,
    _BALANCE_SHEET_SCHEMA,
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
    _GROWTH_SCHEMA,
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


def _table_columns(conn: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return tuple(row[1] for row in rows)


def _migrate_analyst_consensus_schema(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "analystConsensus")
    if "recommendationRating" not in columns:
        return

    conn.execute("DROP TRIGGER IF EXISTS protect_delete_analystConsensus")
    conn.execute("ALTER TABLE analystConsensus RENAME TO analystConsensus_old")
    conn.execute(_ANALYST_CONSENSUS_SCHEMA)

    column_list = ", ".join(_ANALYST_CONSENSUS_COLUMNS)
    conn.execute(
        f"""
        INSERT INTO analystConsensus ({column_list})
        SELECT {column_list}
        FROM analystConsensus_old
        """
    )
    conn.execute("DROP TABLE analystConsensus_old")


def _migrate_balance_sheet_schema(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "balanceSheet")
    removed_columns = {"netDebt", "totalAssets"}
    missing_columns = tuple(
        column for column in _BALANCE_SHEET_COLUMNS if column not in columns
    )
    if not removed_columns.intersection(columns) and not missing_columns:
        return

    if not removed_columns.intersection(columns):
        if "companybookValue" in missing_columns:
            conn.execute("ALTER TABLE balanceSheet ADD COLUMN companybookValue REAL")
        return

    conn.execute("DROP TRIGGER IF EXISTS protect_delete_balanceSheet")
    conn.execute("ALTER TABLE balanceSheet RENAME TO balanceSheet_old")
    conn.execute(_BALANCE_SHEET_SCHEMA)

    shared_columns = tuple(column for column in _BALANCE_SHEET_COLUMNS if column in columns)
    if shared_columns:
        column_list = ", ".join(shared_columns)
        conn.execute(
            f"""
            INSERT INTO balanceSheet ({column_list})
            SELECT {column_list}
            FROM balanceSheet_old
            """
        )
    conn.execute("DROP TABLE balanceSheet_old")


def _migrate_growth_schema(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "growth")
    if "revenueQuarterlyGrowth" not in columns:
        return

    conn.execute("DROP TRIGGER IF EXISTS protect_delete_growth")
    conn.execute("ALTER TABLE growth RENAME TO growth_old")
    conn.execute(_GROWTH_SCHEMA)

    column_list = ", ".join(_GROWTH_COLUMNS)
    conn.execute(
        f"""
        INSERT INTO growth ({column_list})
        SELECT {column_list}
        FROM growth_old
        """
    )
    conn.execute("DROP TABLE growth_old")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the SQLite schema and protection triggers if needed."""

    for statement in _SCHEMA_STATEMENTS:
        conn.execute(statement)
    _migrate_analyst_consensus_schema(conn)
    _migrate_balance_sheet_schema(conn)
    _migrate_growth_schema(conn)
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
