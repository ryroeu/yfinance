"""Authentication-boundary regression tests."""

import unittest
from unittest.mock import Mock, patch

import pandas as pd
from curl_cffi import requests as curl_requests

import yfinance.client as yf
from yfinance.domain.sector import Sector


class TestAuthBoundaryWrappers(unittest.TestCase):
    """Verify public wrappers preserve authentication state correctly."""

    def test_tickers_download_forwards_constructor_session(self):
        """Tickers.download() must forward the container session into bulk download."""
        session = curl_requests.Session(impersonate="chrome")
        captured = {}

        def fake_download(symbols, **kwargs):
            captured["symbols"] = symbols
            captured["session"] = kwargs.get("session")
            return pd.DataFrame()

        with patch("yfinance.tickers._download", side_effect=fake_download):
            tickers = yf.Tickers("AAPL MSFT", session=session)
            tickers.download(period="1d", progress=False, threads=False)

        self.assertEqual(captured["symbols"], ["AAPL", "MSFT"])
        self.assertIs(captured["session"], session)

    def test_tickers_news_reuses_existing_ticker_objects(self):
        """Tickers.news() must not rebuild fresh Ticker objects without session."""
        tickers = yf.Tickers("AAPL MSFT")
        tickers.tickers["AAPL"]._news = [{"title": "AAPL headline"}]
        tickers.tickers["MSFT"]._news = [{"title": "MSFT headline"}]

        with patch("yfinance.tickers.Ticker", side_effect=AssertionError("unexpected")):
            news = tickers.news()

        self.assertEqual(news["AAPL"][0]["title"], "AAPL headline")
        self.assertEqual(news["MSFT"][0]["title"], "MSFT headline")

    def test_domain_ticker_forwards_session(self):
        """Domain.ticker must preserve the domain's session when constructing Ticker."""
        session = curl_requests.Session(impersonate="chrome")
        sector = Sector("technology", session=session)
        sector._symbol = "XLK"

        with patch("yfinance.domain.domain.Ticker", return_value=Mock()) as ticker_ctor:
            _ = sector.ticker

        ticker_ctor.assert_called_once_with("XLK", session=session)