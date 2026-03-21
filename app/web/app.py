"""FastAPI web app for viewing live Yahoo Finance stock data."""

from __future__ import annotations

import sqlite3
import sys
from importlib import import_module
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
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

sql_client = import_module("yfinance.sql.client")
yfinance_exceptions = import_module("yfinance.exceptions")

FETCH_ERRORS = (
    sqlite3.Error,
    KeyError,
    TypeError,
    ValueError,
    RuntimeError,
    yfinance_exceptions.YFException,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (Path(__file__).parent / "templates" / "index.html").read_text()
    return HTMLResponse(content=html)


@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    symbol = symbol.upper()
    results = {}
    for table in TABLES:
        try:
            data = sql_client.fetch(table, symbol)
            results[table] = {"status": "ok", "data": data}
        except FETCH_ERRORS as e:
            results[table] = {"status": "error", "error": str(e)}
    return JSONResponse(content={"symbol": symbol, "tables": results})
