"""Tests for SQL storage helpers."""

import sqlite3
import unittest
from unittest.mock import Mock, patch

import pandas as pd

from yfinance.sql import _db
from yfinance.sql.tables import balance_sheet


class TestBalanceSheetSql(unittest.TestCase):
    """Validate SQL balance-sheet fetch and migration helpers."""

    def test_fetch_includes_company_book_value_from_balance_sheet(self):
        """Balance-sheet SQL fetch should add companybookValue from the statement API."""
        ticker = Mock()
        ticker.info = {
            "totalCash": 100.0,
            "totalDebt": 40.0,
            "debtToEquity": 0.4,
            "currentRatio": 1.2,
            "quickRatio": 1.0,
            "bookValue": 5.0,
        }
        ticker.get_balance_sheet.return_value = pd.DataFrame(
            {
                pd.Timestamp("2024-09-28"): {"StockholdersEquity": 73_733_000_000.0},
                pd.Timestamp("2023-09-30"): {"StockholdersEquity": 62_146_000_000.0},
            }
        )

        with patch("yfinance.sql.tables.balance_sheet.yf.Ticker", return_value=ticker):
            row = balance_sheet.fetch("AAPL")

        self.assertEqual(row["bookValue"], 5.0)
        self.assertEqual(row["companybookValue"], 73_733_000_000.0)

    def test_fetch_returns_none_when_statement_row_missing(self):
        """Balance-sheet SQL fetch should leave companybookValue empty when unavailable."""
        ticker = Mock()
        ticker.info = {"bookValue": 5.0}
        ticker.get_balance_sheet.return_value = pd.DataFrame()

        with patch("yfinance.sql.tables.balance_sheet.yf.Ticker", return_value=ticker):
            row = balance_sheet.fetch("AAPL")

        self.assertEqual(row["bookValue"], 5.0)
        self.assertIsNone(row["companybookValue"])

    def test_balance_sheet_schema_migration_adds_company_book_value_column(self):
        """Schema migration should add companybookValue to existing balanceSheet tables."""
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE balanceSheet (
                symbol TEXT PRIMARY KEY,
                totalCash REAL,
                totalDebt REAL,
                debtToEquity REAL,
                currentRatio REAL,
                quickRatio REAL,
                bookValue REAL
            )
            """
        )

        _db.ensure_schema(conn)

        columns = tuple(
            row[1] for row in conn.execute("PRAGMA table_info(balanceSheet)").fetchall()
        )
        self.assertIn("companybookValue", columns)
