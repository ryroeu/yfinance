"""FastAPI web app for viewing live Yahoo Finance stock data."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from yfinance.sql.client import FETCH_ERRORS, SUPPORTED_TABLES, fetch
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from yfinance.sql.client import FETCH_ERRORS, SUPPORTED_TABLES, fetch

_DIST = Path(__file__).parent / "dist"

app = FastAPI()
app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the Vite-built index.html."""
    return HTMLResponse(content=(_DIST / "index.html").read_text())


@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    """Return fetched stock data for all configured tables as JSON."""
    symbol = symbol.upper()
    results = {}
    for table in SUPPORTED_TABLES:
        try:
            data = fetch(table, symbol)
            results[table] = {"status": "ok", "data": data}
        except FETCH_ERRORS as e:
            results[table] = {"status": "error", "error": str(e)}
    return JSONResponse(content={"symbol": symbol, "tables": results})
