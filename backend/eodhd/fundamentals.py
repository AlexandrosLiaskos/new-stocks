"""
Fundamentals — `/api/fundamentals/{TICKER}`.

Returns a deeply-nested object with sections: General, Highlights,
Valuation, Technicals, SplitsDividends, AnalystRatings, Holders,
InsiderTransactions, Earnings, Financials.

We expose the raw payload and a few small helpers; the orchestrator
projects what's needed into our typed models.
"""
from __future__ import annotations
from typing import Any
from .client import get_client


def fetch_fundamentals(symbol: str) -> dict[str, Any] | None:
    """Full fundamentals object or None when ticker has no record."""
    return get_client().get(f"fundamentals/{symbol}")


def general(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("General") or {}


def highlights(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Highlights") or {}


def valuation(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Valuation") or {}


def technicals(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Technicals") or {}


def analyst_ratings(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("AnalystRatings") or {}


def holders(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Holders") or {}


def insider_transactions(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("InsiderTransactions") or {}


def earnings(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Earnings") or {}


def financials(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("Financials") or {}


def splits_dividends(payload: dict[str, Any] | None) -> dict[str, Any]:
    return (payload or {}).get("SplitsDividends") or {}
