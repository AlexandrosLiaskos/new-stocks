"""Splits + dividends history — `/api/splits/{ticker}` and `/api/div/{ticker}`."""
from __future__ import annotations
import datetime as dt
from typing import Any
from .client import get_client


def fetch_splits(symbol: str,
                 from_: dt.date | str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if from_:
        params["from"] = from_.isoformat() if isinstance(from_, dt.date) else from_
    return get_client().get(f"splits/{symbol}", params) or []


def fetch_dividends(symbol: str,
                    from_: dt.date | str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if from_:
        params["from"] = from_.isoformat() if isinstance(from_, dt.date) else from_
    return get_client().get(f"div/{symbol}", params) or []
