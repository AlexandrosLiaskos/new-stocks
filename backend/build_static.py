"""
Static-site exporter.

Bakes the full app state into `docs/data/` JSON files so the frontend can
run as a pure GitHub Pages site with no backend, no API key in the browser,
no FastAPI server.

Pipeline:
  1. Fetch the widest IPO calendar window from EODHD (default: 1y back +
     30d ahead — the "all" window is too large to enrich daily).
  2. Enrich every row via the existing orchestrator (fundamentals + delayed
     quote, parallel workers).
  3. For each symbol: fetch full dossier payload and write per-symbol JSON.
  4. Read every intelligence record from SQLite and write per-symbol JSON.
  5. Build a search index from listings + intelligence symbols.
  6. Write manifest with build timestamp + counts.

Run from project root:
    python -m backend.build_static
    python -m backend.build_static --window 1y          # default
    python -m backend.build_static --window all         # 10y, slow
    python -m backend.build_static --skip-full          # only top-level lists

Env: EODHD_API_KEY must be set.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import intel_db, orchestrator
from .schema import Region

log = logging.getLogger("build_static")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA = DOCS / "data"

WINDOW_DAYS: dict[str, int] = {
    "30d": 30, "90d": 90, "6m": 180, "1y": 365, "all": 3650,
}


def _window_to_dates(window: str) -> tuple[str, str]:
    today = dt.date.today()
    days_back = WINDOW_DAYS.get(window, 365)
    return (
        (today - dt.timedelta(days=days_back)).isoformat(),
        (today + dt.timedelta(days=30)).isoformat(),
    )


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))


def _clean_data_dir() -> None:
    if DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- listings

def export_listings(window: str) -> list[dict]:
    from_, to_ = _window_to_dates(window)
    log.info("listings: building %s window (%s → %s)", window, from_, to_)
    try:
        rows = orchestrator.build_listings(from_=from_, to_=to_)
        items = [s.model_dump(mode="json") for s in rows]
    except Exception as e:
        log.warning("listings: EODHD fetch failed (%s) — writing empty listings", e)
        items = []
    _write_json(DATA / "listings.json", items)
    log.info("listings: %d rows written", len(items))
    return items


# ---------------------------------------------------------------- per-symbol full

def export_full_details(symbols: list[str], max_workers: int = 12) -> int:
    """One JSON per symbol with the dossier payload."""
    full_dir = DATA / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    def one(sym: str) -> tuple[str, bool]:
        try:
            d = orchestrator.build_full_detail(sym)
            _write_json(full_dir / f"{_safe_filename(sym)}.json", d.model_dump(mode="json"))
            return sym, True
        except Exception as e:
            log.warning("full %s failed: %s", sym, e)
            return sym, False

    ok = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(one, s) for s in symbols]
        for i, fut in enumerate(as_completed(futs), 1):
            sym, success = fut.result()
            if success:
                ok += 1
            if i % 25 == 0:
                log.info("full: %d/%d done (%.1fs)", i, len(symbols), time.time() - started)
    log.info("full: %d/%d written in %.1fs", ok, len(symbols), time.time() - started)
    return ok


def _safe_filename(symbol: str) -> str:
    """Symbols like '0700.HK' are safe; '/' or backslashes would be a problem."""
    return symbol.replace("/", "_").replace("\\", "_")


# ---------------------------------------------------------------- intelligence

def export_intelligence() -> int:
    intel_dir = DATA / "intelligence"
    intel_dir.mkdir(parents=True, exist_ok=True)
    syms = intel_db.list_symbols()
    for s in syms:
        rec = intel_db.get(s)
        if rec:
            _write_json(intel_dir / f"{_safe_filename(s)}.json", rec)
    log.info("intelligence: %d records written", len(syms))
    return len(syms)


# ---------------------------------------------------------------- search index

def export_search_index(listings: list[dict]) -> int:
    """Lightweight, client-side filterable. Includes listing rows + symbols
    that have an intelligence record but aren't in the current listings."""
    by_sym: dict[str, dict] = {}
    for s in listings:
        by_sym[s["symbol"]] = {
            "symbol": s["symbol"],
            "name": s.get("name") or s["symbol"],
            "exchange": s.get("exchange"),
            "country": s.get("country"),
            "type": s.get("status"),
            "currency": s.get("currency"),
        }
    for sym in intel_db.list_symbols():
        if sym not in by_sym:
            rec = intel_db.get(sym) or {}
            by_sym[sym] = {
                "symbol": sym,
                "name": rec.get("name") or sym,
                "exchange": None,
                "country": None,
                "type": "researched",
                "currency": None,
            }
    items = list(by_sym.values())
    _write_json(DATA / "search.json", items)
    log.info("search: %d entries indexed", len(items))
    return len(items)


# ---------------------------------------------------------------- manifest

def export_manifest(*, window: str, listings_count: int, full_count: int,
                    intel_count: int, search_count: int) -> None:
    manifest = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": window,
        "counts": {
            "listings": listings_count,
            "full_details": full_count,
            "intelligence": intel_count,
            "search_entries": search_count,
        },
        "regions_known": [r.value for r in Region],
        "capabilities": {
            "eod_history": False,            # static build — chart not in plan anyway
            "live_quote_baked_in": True,
            "fundamentals": True,
            "ipo_calendar": True,
            "intelligence": True,
        },
        "notes": (
            "Static snapshot. All data baked at build time. Re-run "
            "`python -m backend.build_static` to refresh."
        ),
    }
    _write_json(DATA / "manifest.json", manifest)


# ---------------------------------------------------------------- main

def main() -> int:
    p = argparse.ArgumentParser(description="Build the static site into docs/")
    p.add_argument("--window", default="1y", choices=list(WINDOW_DAYS.keys()))
    p.add_argument("--skip-full", action="store_true",
                   help="Skip per-symbol full dossier export (fast, but dossier is then empty).")
    p.add_argument("--max-workers", type=int, default=12)
    args = p.parse_args()

    intel_db.init_db()
    _clean_data_dir()

    listings = export_listings(args.window)
    syms = [s["symbol"] for s in listings]

    full_count = 0
    if not args.skip_full and syms:
        full_count = export_full_details(syms, max_workers=args.max_workers)

    intel_count = export_intelligence()
    search_count = export_search_index(listings)

    export_manifest(
        window=args.window,
        listings_count=len(listings),
        full_count=full_count,
        intel_count=intel_count,
        search_count=search_count,
    )

    log.info("DONE. docs/ ready to commit + push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
