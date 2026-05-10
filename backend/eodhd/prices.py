"""
EOD historical OHLCV (`/api/eod/{ticker}`) and live (15-min delayed) quote
(`/api/real-time/{ticker}`).
"""
from __future__ import annotations
import datetime as dt
from typing import Any
from .client import get_client


def eod_history(symbol: str,
                from_: dt.date | str | None = None,
                to_: dt.date | str | None = None,
                period: str = "d") -> list[dict[str, Any]]:
    """Return list of OHLCV rows. period: 'd' (daily), 'w' (weekly), 'm' (monthly)."""
    params: dict[str, Any] = {"period": period}
    if from_:
        params["from"] = from_.isoformat() if isinstance(from_, dt.date) else from_
    if to_:
        params["to"] = to_.isoformat() if isinstance(to_, dt.date) else to_
    payload = get_client().get(f"eod/{symbol}", params)
    return payload or []


def live_quote(symbol: str) -> dict[str, Any] | None:
    """Latest snapshot — real-time on US (intraday tier), 15-min delayed otherwise."""
    payload = get_client().get(f"real-time/{symbol}")
    if isinstance(payload, dict) and payload.get("code"):
        return payload
    return None


# Convenience: pre-defined ranges → (period, days_back)
RANGE_PRESETS: dict[str, tuple[str, int | None]] = {
    "1d": ("d", 7),       # last week of dailies (no intraday on Fundamentals tier)
    "1w": ("d", 14),
    "1mo": ("d", 35),
    "6mo": ("d", 200),
    "1y": ("d", 380),
    "5y": ("w", 5 * 380),
    "max": ("m", None),
}


def history_for_range(symbol: str, range_: str) -> list[dict[str, Any]]:
    period, days_back = RANGE_PRESETS.get(range_, ("d", 380))
    today = dt.date.today()
    from_ = today - dt.timedelta(days=days_back) if days_back else None
    return eod_history(symbol, from_=from_, to_=today, period=period)
