"""
FastAPI app for New Stocks — pure EODHD data layer.

Slim orchestrator: every route delegates to `orchestrator` and caches the
result. No fan-out across multiple sources, no aggregation, no scraping.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import logging
from pathlib import Path
from typing import Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import orchestrator
from . import intel_store as intel_db   # filesystem-backed; same public API as the old SQLite module
from .cache import (
    TTL_EXCHANGES, TTL_FULL, TTL_HISTORY_FROZEN, TTL_HISTORY_LIVE, TTL_LIST,
    TTL_SEARCH, bust, cached,
)
from .capabilities import CAPS, run_startup_probe
from .eodhd.client import EODHDError
from .eodhd import prices as eodhd_prices

log = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Probe runs in a thread so a slow EODHD doesn't block server boot.
    import asyncio
    try:
        await asyncio.wait_for(asyncio.to_thread(run_startup_probe), timeout=10.0)
    except Exception as e:
        log.warning("startup probe skipped: %s", e)
    yield


app = FastAPI(title="New Stocks", version="2.1", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)


# ---------------------------------------------------------------- list

# Period shortcuts → days of lookback. Lookahead is fixed at 30d because
# EODHD's IPO calendar only has ~2-3 weeks of upcoming filings.
PERIOD_DAYS: dict[str, int] = {
    "7d": 7, "30d": 30, "90d": 90,
    "6m": 180, "1y": 365, "all": 3650,  # ~10 years (EODHD covers from 2015)
}
DEFAULT_PERIOD = "30d"


def _period_window(period: str) -> tuple[str, str]:
    today = dt.date.today()
    days_back = PERIOD_DAYS.get(period, PERIOD_DAYS[DEFAULT_PERIOD])
    return (
        (today - dt.timedelta(days=days_back)).isoformat(),
        (today + dt.timedelta(days=30)).isoformat(),
    )


def _build_listings_payload(period: str) -> list[dict]:
    from_, to_ = _period_window(period)
    return [s.model_dump(mode="json")
            for s in orchestrator.build_listings(from_=from_, to_=to_)]


def _listings(period: str = DEFAULT_PERIOD, force: bool = False) -> list[dict]:
    if period not in PERIOD_DAYS:
        period = DEFAULT_PERIOD
    if force:
        bust(f"list:{period}")
    return cached(f"list:{period}", TTL_LIST, _build_listings_payload, period)


@app.get("/api/new-stocks")
def api_list(
    period: str = Query(DEFAULT_PERIOD, description="period shortcut: 7d|30d|90d|6m|1y|all"),
    status: Optional[str] = Query(None, description="comma-separated: priced,upcoming,filed"),
    region: Optional[str] = Query(None, description="comma-separated regions e.g. US,UK,EU,ASIA,INDIA,OCEANIA"),
):
    items = _listings(period=period)
    if status:
        wanted = {s.strip().lower() for s in status.split(",")}
        items = [s for s in items if s.get("status") in wanted]
    if region:
        wanted_r = {r.strip().upper() for r in region.split(",")}
        items = [s for s in items if (s.get("region") or "").upper() in wanted_r]
    return items


@app.get("/api/new-stocks/refresh")
def api_refresh(period: str = Query(DEFAULT_PERIOD)):
    return _listings(period=period, force=True)


# ---------------------------------------------------------------- detail

@app.get("/api/stock/{symbol}/full")
def api_stock_full(symbol: str):
    """Full dossier payload — heavy, lazy-loaded on dossier open."""
    payload = cached(
        f"full:{symbol}",
        TTL_FULL,
        lambda: orchestrator.build_full_detail(symbol).model_dump(mode="json"),
    )
    return payload


# ---------------------------------------------------------------- history


def _eod_disabled_response() -> JSONResponse:
    """Short-circuit response when the active plan can't reach EOD endpoints."""
    return JSONResponse(
        {
            "error": "eodhd_auth_error",
            "status": 403,
            "message": "EOD historical prices are not on your EODHD plan. "
                       "Add 'EOD All World' (€19.99/mo) or upgrade to All-In-One.",
        },
        status_code=401,
    )


@app.get("/api/stock/{symbol}/history")
def api_history(symbol: str, range: str = "1y"):
    if not CAPS["eod_history"]:
        return _eod_disabled_response()
    ttl = TTL_HISTORY_LIVE if range in ("1d", "1w") else TTL_HISTORY_FROZEN
    rows = cached(f"hist:{symbol}:{range}",
                  ttl,
                  lambda: [r.model_dump() for r in orchestrator.history_rows(symbol, range)])
    return rows


# ---------------------------------------------------------------- CSV

@app.get("/api/stock/{symbol}/download.csv")
def api_csv(symbol: str):
    if not CAPS["eod_history"]:
        return _eod_disabled_response()
    rows = eodhd_prices.eod_history(symbol)
    if not rows:
        raise HTTPException(404, "no history")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"])
    for r in rows:
        w.writerow([
            r.get("date", ""),
            f"{r['open']:.4f}" if isinstance(r.get("open"), (int, float)) else "",
            f"{r['high']:.4f}" if isinstance(r.get("high"), (int, float)) else "",
            f"{r['low']:.4f}"  if isinstance(r.get("low"),  (int, float)) else "",
            f"{r['close']:.4f}" if isinstance(r.get("close"), (int, float)) else "",
            f"{r['adjusted_close']:.4f}" if isinstance(r.get("adjusted_close"), (int, float)) else "",
            int(r["volume"]) if isinstance(r.get("volume"), (int, float)) else "",
        ])
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{symbol.upper()}_history.csv"'},
    )


# ---------------------------------------------------------------- lean overview (declared LAST so /full, /history, /download.csv match first)

@app.get("/api/stock/{symbol}")
def api_stock(symbol: str):
    """Lean overview for the row click — uses cached list entry if present."""
    try:
        for s in _listings():
            if s.get("symbol", "").upper() == symbol.upper():
                return s
    except Exception:
        pass  # IPO list unavailable; fall through to direct fundamentals
    # Not in current IPO list — build a one-off bare overview from fundamentals
    full = cached(
        f"full:{symbol}",
        TTL_FULL,
        lambda: orchestrator.build_full_detail(symbol).model_dump(mode="json"),
    )
    return full["base"]


# ---------------------------------------------------------------- search

@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1)):
    payload = cached(
        f"search:{q.lower()}",
        TTL_SEARCH,
        lambda: [h.model_dump() for h in orchestrator.search_hits(q)],
    )
    return payload


# ---------------------------------------------------------------- exchanges

@app.get("/api/exchanges")
def api_exchanges():
    payload = cached(
        "exchanges:list",
        TTL_EXCHANGES,
        lambda: [e.model_dump(mode="json") for e in orchestrator.exchanges_list()],
    )
    return payload


# ---------------------------------------------------------------- capabilities

@app.get("/api/capabilities")
def api_capabilities():
    """What can the active EODHD plan actually do?"""
    return dict(CAPS)


# ---------------------------------------------------------------- intelligence

@app.get("/api/stock/{symbol}/intelligence")
def api_intelligence(symbol: str):
    """Structured business-intelligence record for one stock (or 404)."""
    record = intel_db.get(symbol)
    if not record:
        raise HTTPException(404, "no intelligence record")
    return record


@app.get("/api/intelligence/missing")
def api_intelligence_missing(period: str = Query(DEFAULT_PERIOD),
                             max_age_days: int = 7,
                             limit: int = 200):
    """List of symbols in the current IPO feed that need (re-)researching.

    Used by the `/research-stocks` slash command to decide what to work on.
    A symbol is 'stale' if it's missing entirely or its record is older
    than `max_age_days`.
    """
    items = _listings(period=period)
    by_sym = {it["symbol"]: it for it in items}
    stale = intel_db.list_stale(list(by_sym.keys()), max_age_days=max_age_days)
    return [
        {
            "symbol": s,
            "name": by_sym[s].get("name"),
            "exchange": by_sym[s].get("exchange"),
            "country": by_sym[s].get("country"),
            "sector": by_sym[s].get("sector"),
            "industry": by_sym[s].get("industry"),
            "status": by_sym[s].get("status"),
            "list_date": by_sym[s].get("list_date"),
            "web_url": by_sym[s].get("web_url"),
            "prospectus_url": by_sym[s].get("prospectus_url"),
            "description": by_sym[s].get("description"),
        }
        for s in stale[:limit]
    ]


@app.get("/api/intelligence/stats")
def api_intelligence_stats():
    return intel_db.stats()


# ---------------------------------------------------------------- frontend

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/")
def root():
    return FileResponse(FRONTEND / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")


# ---------------------------------------------------------------- error mapping

@app.exception_handler(EODHDError)
async def _eodhd_error(_, exc: EODHDError):
    log.warning("eodhd error %s on %s: %s", exc.status, exc.url, exc)
    if exc.status in (401, 403):
        return JSONResponse(
            {
                "error": "eodhd_auth_error",
                "status": exc.status,
                "message": "EODHD API key missing, invalid, or your plan does not "
                           "include this endpoint. Set EODHD_API_KEY and restart "
                           "the server.",
            },
            status_code=401,
        )
    return JSONResponse(
        {"error": "eodhd_api_error", "status": exc.status, "message": str(exc)},
        status_code=502 if exc.status and exc.status >= 500 else 400,
    )


@app.exception_handler(Exception)
async def _all_errors(_, exc: Exception):
    log.exception("unhandled: %s", exc)
    return JSONResponse({"error": "server_error", "message": str(exc)}, status_code=500)
