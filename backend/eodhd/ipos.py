"""
IPO calendar — `/api/calendar/ipos`.

Coverage window: January 2015 → ~3 weeks ahead. Truly global
(US, Europe, Hong Kong, Tokyo, Shanghai, NSE/BSE, etc.).
"""
from __future__ import annotations
import datetime as dt
from typing import Any
from .client import get_client


def fetch_ipos(from_: dt.date | str | None = None,
               to_: dt.date | str | None = None) -> list[dict[str, Any]]:
    """Return raw IPO rows for the given date window.

    Defaults: from = today − 60d, to = today + 30d (covers recently
    priced + filed-but-not-yet-priced).
    """
    today = dt.date.today()
    if from_ is None:
        from_ = today - dt.timedelta(days=60)
    if to_ is None:
        to_ = today + dt.timedelta(days=30)
    if isinstance(from_, dt.date):
        from_ = from_.isoformat()
    if isinstance(to_, dt.date):
        to_ = to_.isoformat()

    payload = get_client().get("calendar/ipos", {"from": from_, "to": to_})
    if not payload:
        return []
    return list(payload.get("ipos") or [])


def classify_status(deal_type: str | None, list_date: str | None) -> str:
    """Map EODHD's `deal_type` to our (priced|upcoming|filed) status."""
    today = dt.date.today().isoformat()
    dt_norm = (deal_type or "").strip().lower()
    if dt_norm in ("priced", "completed", "trading"):
        return "priced"
    if list_date:
        if list_date <= today and dt_norm in ("expected", ""):
            # Expected date already past — treat as priced (likely listed)
            return "priced"
        if list_date > today:
            return "upcoming"
    if dt_norm == "expected":
        return "upcoming"
    return "filed"
