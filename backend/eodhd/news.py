"""
News API — `/api/news?s={symbol}&limit=N`.

Confirmed available on the user's Fundamentals Data Feed plan
(News API Data toggle: ON in the EODHD account UI).

Returns an array of news items: {date, title, content, link, symbols,
tags, sentiment {polarity, neg, neu, pos}}.
"""
from __future__ import annotations
from typing import Any
from .client import get_client


def fetch_news(symbol: str, limit: int = 10) -> list[dict[str, Any]]:
    """Latest news items for a single symbol. Returns [] on any failure."""
    try:
        payload = get_client().get("news", {"s": symbol, "limit": limit, "offset": 0})
    except Exception:
        return []
    return payload or []
