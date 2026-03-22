"""Tests for SQL schema bootstrapping and protected delete behavior."""

import sqlite3
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.context import yfinance as yf

from yfinance.sql import _db
from yfinance.sql import client as sql_client


class TestSqlProtection(unittest.TestCase):
    """Validate SQL schema setup and guarded delete semantics."""

    @classmethod
    def setUpClass(cls):
        cls._ = yf

    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        self.db_path = Path(temp_dir) / "yfinance.db"
        original_db_path = _db.DB_PATH
        _db.DB_PATH = self.db_path
        self.addCleanup(setattr, _db, "DB_PATH", original_db_path)

    def _seed_symbol(self, symbol: str) -> None:
        with _db.get_connection(allow_protected_deletes=True) as conn:
            conn.execute(
                "INSERT INTO fastInfo (symbol, exchange, status, currency) VALUES (?, ?, ?, ?)",
                (symbol, "NYSE", "active", "USD"),
            )
            conn.execute(
                "INSERT INTO analystConsensus (symbol, targetMeanPrice) VALUES (?, ?)",
                (symbol, 101.0),
            )
            conn.execute(
                "INSERT INTO balanceSheet (symbol, totalCash) VALUES (?, ?)",
                (symbol, 1000.0),
            )
            conn.execute(
                "INSERT INTO companyProfile (symbol, longName) VALUES (?, ?)",
                (symbol, f"{symbol} Corp"),
            )
            conn.execute(
                "INSERT INTO dividends (symbol, dividendRate) VALUES (?, ?)",
                (symbol, 1.5),
            )
            conn.execute(
                "INSERT INTO growth (symbol, revenueGrowth) VALUES (?, ?)",
                (symbol, 0.2),
            )
            conn.execute(
                "INSERT INTO profitability (symbol, profitMargins) VALUES (?, ?)",
                (symbol, 0.15),
            )
            conn.execute(
                "INSERT INTO valuation (symbol, trailingPE) VALUES (?, ?)",
                (symbol, 24.0),
            )

    def test_connection_enables_foreign_keys_and_creates_triggers(self):
        """Connections should enable FKs and install one trigger per protected table."""

        with _db.get_connection() as conn:
            foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            trigger_names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                ).fetchall()
            }

        self.assertEqual(foreign_keys, 1)
        expected_triggers = {
            f"protect_delete_{table_name}" for table_name in _db.protected_tables()
        }
        self.assertEqual(trigger_names, expected_triggers)

    def test_direct_deletes_are_blocked_while_upserts_still_refresh(self):
        """Direct deletes should fail while UPSERT-style refreshes still work."""

        self._seed_symbol("AAPL")
        sql_client.save(
            "fast_info",
            "FASTONLY",
            {"exchange": "NASDAQ", "status": "active", "currency": "USD", "open": 10.0},
        )
        sql_client.save(
            "fast_info",
            "FASTONLY",
            {"exchange": "NASDAQ", "status": "active", "currency": "CAD", "open": 12.5},
        )

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "Rows in analystConsensus are protected",
        ):
            with _db.get_connection() as conn:
                conn.execute("DELETE FROM analystConsensus WHERE symbol = ?", ("AAPL",))

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "Rows in fastInfo are protected",
        ):
            with _db.get_connection() as conn:
                conn.execute("DELETE FROM fastInfo WHERE symbol = ?", ("FASTONLY",))

        with _db.get_connection() as conn:
            row = conn.execute(
                "SELECT currency, open FROM fastInfo WHERE symbol = ?",
                ("FASTONLY",),
            ).fetchone()
            count = conn.execute(
                "SELECT COUNT(*) FROM fastInfo WHERE symbol = ?",
                ("FASTONLY",),
            ).fetchone()[0]

        self.assertEqual(row, ("CAD", 12.5))
        self.assertEqual(count, 1)

    def test_audited_delete_removes_only_selected_symbols(self):
        """Audited deletes should remove only the requested symbol across tables."""

        self._seed_symbol("AUDIT")
        self._seed_symbol("KEEP")

        sql_client.delete_symbols(["AUDIT"])

        with _db.get_connection(allow_protected_deletes=True) as conn:
            for table_name in _db.protected_tables():
                deleted_count = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE symbol = ?",
                    ("AUDIT",),
                ).fetchone()[0]
                kept_count = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE symbol = ?",
                    ("KEEP",),
                ).fetchone()[0]
                self.assertEqual(deleted_count, 0)
                self.assertEqual(kept_count, 1)


if __name__ == "__main__":
    unittest.main()
