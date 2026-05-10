"""EODHD API client and typed endpoint modules.

Tier required: Fundamentals Data Feed (€59.99/mo) — covers calendar/ipos,
fundamentals, eod, real-time (15-min delayed), search, exchanges-list,
splits, div, insider-transactions.

API key is read from env var EODHD_API_KEY (or `demo` for limited tickers
like AAPL.US, MCD.US, BTC-USD.CC during development).
"""
from .client import EODHDClient, EODHDError, get_client

__all__ = ["EODHDClient", "EODHDError", "get_client"]
