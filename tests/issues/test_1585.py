"""Regression test for issue #1585: last trading hour missing for Saudi stocks.

The original report showed that for Saudi market tickers (e.g. 2222.SR / Aramco),
hourly history omitted the 15:00–16:00 bar even though the Tadawul exchange trades
until 15:20 local time (Asia/Riyadh, UTC+3).

Two mechanisms in the refactored codebase prevent this:

1. When ``period='1mo'`` is requested without explicit start/end, ``state.end``
   remains ``None``, so the last-bar truncation guard in ``_extract_quotes`` is
   never reached.

2. ``fix_yahoo_returning_prepost_unrequested`` compares bar timestamps against the
   ``end`` field from Yahoo's ``tradingPeriods`` metadata.  For Saudi tickers
   Yahoo reports ``end = 15:20``, so the 15:00 bar (which starts before 15:20)
   satisfies ``bar_time < end`` and is correctly retained.  Only a bar whose
   timestamp is >= 15:20 (e.g. a hypothetical 15:30 bar) would be pruned.
"""

import json
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import yfinance.client as yf

from ..close_candidates_support import call_private


def _make_response(payload):
    response = Mock(status_code=200)
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


class TestIssue1585(unittest.TestCase):
    """Saudi market 15:00 bar must not be dropped by the pre/post pruning filter."""

    # Unix timestamps (UTC seconds from epoch) for 2023-06-07, Asia/Riyadh (UTC+3).
    # 2023-06-07 00:00:00 UTC = 1686096000
    _BAR_10 = 1686121200  # 2023-06-07 10:00:00+03:00  (07:00 UTC)
    _BAR_11 = 1686124800  # 2023-06-07 11:00:00+03:00  (08:00 UTC)
    _BAR_12 = 1686128400  # 2023-06-07 12:00:00+03:00  (09:00 UTC)
    _BAR_13 = 1686132000  # 2023-06-07 13:00:00+03:00  (10:00 UTC)
    _BAR_14 = 1686135600  # 2023-06-07 14:00:00+03:00  (11:00 UTC)
    _BAR_15 = 1686139200  # 2023-06-07 15:00:00+03:00  (12:00 UTC)  ← must survive
    _MARKET_OPEN  = 1686121200  # 10:00:00+03:00
    _MARKET_CLOSE = 1686140400  # 15:20:00+03:00  (12:20 UTC)

    def _saudi_hourly_payload(self, extra_timestamps=None, extra_prices=None):
        """Return a minimal Yahoo chart payload for 2222.SR with six hourly bars.

        ``tradingPeriods`` in the metadata mirrors the real Tadawul schedule:
        open 10:00, close 15:20 (Asia/Riyadh).  The six bars cover 10–15 local.
        """
        timestamps = [
            self._BAR_10,
            self._BAR_11,
            self._BAR_12,
            self._BAR_13,
            self._BAR_14,
            self._BAR_15,
        ]
        opens  = [32.50, 32.45, 32.45, 32.40, 32.40, 32.40]
        highs  = [32.50, 32.50, 32.50, 32.45, 32.45, 32.45]
        lows   = [32.35, 32.40, 32.35, 32.35, 32.30, 32.30]
        closes = [32.45, 32.45, 32.40, 32.40, 32.40, 32.40]
        vols   = [562639, 360020, 392409, 396132, 1205491, 300000]

        if extra_timestamps:
            ep = extra_prices or {}
            timestamps += extra_timestamps
            opens  += [ep.get("open",   32.40)] * len(extra_timestamps)
            highs  += [ep.get("high",   32.45)] * len(extra_timestamps)
            lows   += [ep.get("low",    32.30)] * len(extra_timestamps)
            closes += [ep.get("close",  32.40)] * len(extra_timestamps)
            vols   += [ep.get("volume", 50000)] * len(extra_timestamps)

        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "SAR",
                            "instrumentType": "EQUITY",
                            "exchangeTimezoneName": "Asia/Riyadh",
                            "validRanges": ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
                            "regularMarketPrice": 32.4,
                            "tradingPeriods": [
                                [
                                    {
                                        "timezone": "AST",
                                        "gmtoffset": 10800,
                                        "start": self._MARKET_OPEN,
                                        "end": self._MARKET_CLOSE,
                                    }
                                ]
                            ],
                        },
                        "timestamp": timestamps,
                        "indicators": {
                            "quote": [
                                {
                                    "open": opens,
                                    "high": highs,
                                    "low": lows,
                                    "close": closes,
                                    "volume": vols,
                                }
                            ],
                            "adjclose": [{"adjclose": closes[:]}],
                        },
                    }
                ],
                "error": None,
            }
        }

    def _get_history(self, payload, **kwargs):
        response = _make_response(payload)
        ticker = yf.Ticker("2222.SR")
        with patch.object(ticker, "_get_ticker_tz", return_value="Asia/Riyadh"):
            history = call_private(ticker, "_lazy_load_price_history")
        client = history.get_data_client()
        with (
            patch.object(client, "get", return_value=response),
            patch.object(client, "cache_get", return_value=response),
        ):
            return history.history(**kwargs)

    def test_last_trading_hour_bar_is_not_dropped(self):
        """All six hourly bars including 15:00 must be returned for period='1mo'."""
        data = self._get_history(
            self._saudi_hourly_payload(),
            period="1mo",
            interval="1h",
        )

        self.assertIsInstance(data, pd.DataFrame)
        self.assertFalse(data.empty, "Expected non-empty DataFrame for 2222.SR hourly data")
        self.assertEqual(
            len(data),
            6,
            f"Expected 6 hourly bars (10–15 local), got {len(data)}: {data.index.tolist()}",
        )

        last_bar_local = pd.Timestamp(data.index[-1]).tz_convert("Asia/Riyadh")
        self.assertEqual(
            last_bar_local.hour,
            15,
            f"Last bar should be at 15:00 local, got {last_bar_local}",
        )
        self.assertEqual(last_bar_local.minute, 0)

    def test_bar_at_market_close_boundary_is_not_dropped(self):
        """The 15:00 bar (close < 15:20 market end) must not be treated as post-market."""
        data = self._get_history(
            self._saudi_hourly_payload(),
            period="1mo",
            interval="1h",
            prepost=False,
        )

        bar_hours_local = [
            pd.Timestamp(ts).tz_convert("Asia/Riyadh").hour
            for ts in pd.DatetimeIndex(data.index)
        ]
        self.assertIn(
            15,
            bar_hours_local,
            f"15:00 bar should be present; bar hours found: {bar_hours_local}",
        )

    def test_bar_after_market_close_is_pruned(self):
        """A synthetic bar at 15:30 (past the 15:20 market close) must be dropped."""
        bar_15_30 = self._BAR_15 + 1800  # 15:30 local = 12:30 UTC
        data = self._get_history(
            self._saudi_hourly_payload(
                extra_timestamps=[bar_15_30],
                extra_prices={
                    "open": 32.4,
                    "high": 32.4,
                    "low": 32.3,
                    "close": 32.35,
                    "volume": 50000,
                },
            ),
            period="1mo",
            interval="1h",
        )

        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(
            len(data),
            6,
            f"Bar after market close (15:30) should be pruned; "
            f"got {len(data)} bars: {data.index.tolist()}",
        )
        last_bar_local = pd.Timestamp(data.index[-1]).tz_convert("Asia/Riyadh")
        self.assertEqual(
            last_bar_local.hour,
            15,
            f"Last bar should still be 15:00 after pruning 15:30; got {last_bar_local}",
        )
        self.assertEqual(last_bar_local.minute, 0)
