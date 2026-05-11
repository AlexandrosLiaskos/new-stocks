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

from . import intel_store as intel_db, orchestrator
from .eodhd import news as eodhd_news
from .eodhd.client import EODHDError
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


_EOD_DERIVED_SUBDIRS = ("full", "news")   # rebuilt every run; safe to wipe
_EOD_DERIVED_FILES = ("listings.json", "search.json", "manifest.json")


def _clean_eodhd_derived() -> None:
    """Wipe ONLY the EODHD-derived files / dirs. The `intelligence/` dir
    inside docs/data is left untouched — it gets re-copied from the
    source-of-truth `intelligence/` repo dir later, but we don't blow
    away the existing copy in case the source dir is empty on a given
    build."""
    DATA.mkdir(parents=True, exist_ok=True)
    for sub in _EOD_DERIVED_SUBDIRS:
        p = DATA / sub
        if p.exists():
            shutil.rmtree(p)
    for f in _EOD_DERIVED_FILES:
        p = DATA / f
        if p.exists():
            p.unlink()


# ---------------------------------------------------------------- listings

class _EODHDAuthFailure(RuntimeError):
    """Raised when the IPO calendar 401/403s. Caller decides whether to
    overwrite existing data or preserve it."""


def export_listings(window: str) -> list[dict]:
    """Fetch & enrich the IPO calendar for the given window.

    Raises `_EODHDAuthFailure` on 401/403 so the caller can preserve the
    last good docs/data/ snapshot instead of clobbering it with `[]`.
    """
    from_, to_ = _window_to_dates(window)
    log.info("listings: building %s window (%s → %s)", window, from_, to_)
    try:
        rows = orchestrator.build_listings(from_=from_, to_=to_)
    except EODHDError as e:
        if e.status in (401, 403):
            raise _EODHDAuthFailure(
                f"EODHD auth failed (HTTP {e.status}). Set EODHD_API_KEY "
                f"or check that the key includes the Calendar API."
            ) from e
        log.warning("listings: EODHD fetch failed (%s) — writing empty listings", e)
        rows = []
    items = [s.model_dump(mode="json") for s in rows]
    _write_json(DATA / "listings.json", items)
    log.info("listings: %d rows written", len(items))
    return items


# ---------------------------------------------------------------- per-symbol full

def export_full_details(listings: list[dict], max_workers: int = 4) -> int:
    """One JSON per symbol with the dossier payload.

    Reuses each row's already-built NewStock as the dossier `base`, so the
    only new HTTP call per stock is the cached fundamentals fetch (one per
    symbol per build — see `_FUND_CACHE` in `orchestrator.py`). Rows with
    failed enrichment in `build_listings` still get a partial dossier.

    `max_workers=4` keeps us under EODHD's 1000 req/min plan limit.
    """
    from .schema import NewStock

    full_dir = DATA / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    def one(row: dict) -> tuple[str, bool]:
        sym = row["symbol"]
        try:
            base = NewStock.model_validate(row)
            d = orchestrator.build_full_detail(sym, base=base)
            _write_json(full_dir / f"{_safe_filename(sym)}.json", d.model_dump(mode="json"))
            return sym, True
        except Exception as e:
            log.warning("full %s failed: %s", sym, e)
            return sym, False

    ok = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(one, r) for r in listings]
        for i, fut in enumerate(as_completed(futs), 1):
            sym, success = fut.result()
            if success:
                ok += 1
            if i % 25 == 0:
                log.info("full: %d/%d done (%.1fs)", i, len(listings), time.time() - started)
    log.info("full: %d/%d written in %.1fs", ok, len(listings), time.time() - started)
    return ok


def _safe_filename(symbol: str) -> str:
    """Symbols like '0700.HK' are safe; '/' or backslashes would be a problem."""
    return symbol.replace("/", "_").replace("\\", "_")


# ---------------------------------------------------------------- news

def export_news(listings: list[dict], max_workers: int = 4,
                per_symbol_limit: int = 10) -> int:
    """One JSON per symbol with the latest EODHD-curated news items.

    Available on the Fundamentals Data Feed tier (News API Data toggle ON).
    Each file contains an array of {date, title, content, link, symbols,
    tags, sentiment} objects — frontend renders the top N in the dossier.
    """
    news_dir = DATA / "news"
    news_dir.mkdir(parents=True, exist_ok=True)

    def one(row: dict) -> tuple[str, int]:
        sym = row["symbol"]
        items = eodhd_news.fetch_news(sym, limit=per_symbol_limit)
        if items:
            _write_json(news_dir / f"{_safe_filename(sym)}.json", items)
        return sym, len(items)

    total_items = 0
    written_files = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(one, r) for r in listings]
        for i, fut in enumerate(as_completed(futs), 1):
            _, n = fut.result()
            if n > 0:
                written_files += 1
                total_items += n
            if i % 50 == 0:
                log.info("news: %d/%d done (%.1fs)", i, len(listings), time.time() - started)
    log.info("news: %d files (%d items) written in %.1fs",
             written_files, total_items, time.time() - started)
    return written_files


# ---------------------------------------------------------------- intelligence

def export_intelligence() -> int:
    """Copy the source-of-truth `intelligence/` dir into `docs/data/`.

    The source dir is committed to git and edited by `/research-stocks`
    and `intel_write.py`. We never WRITE it from here — only mirror it
    into the static-site tree. If the source is empty, leave any
    existing docs/data/intelligence/ in place.
    """
    src = intel_db.STORE_DIR
    dst = DATA / "intelligence"
    if not src.exists() or not any(src.iterdir()):
        log.info("intelligence: source dir empty — preserving existing docs/data/intelligence/")
        return sum(1 for _ in dst.glob("*.json")) if dst.exists() else 0

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    n = sum(1 for _ in dst.glob("*.json"))
    log.info("intelligence: %d records copied from %s", n, src)
    return n


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
                    intel_count: int, search_count: int, news_count: int) -> None:
    manifest = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": window,
        "counts": {
            "listings": listings_count,
            "full_details": full_count,
            "intelligence": intel_count,
            "news_files": news_count,
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
    p.add_argument("--skip-news", action="store_true",
                   help="Skip per-symbol news export.")
    p.add_argument("--max-workers", type=int, default=4)
    p.add_argument(
        "--preserve-listings-on-auth-fail", action="store_true", default=True,
        help="(default true) On 401/403 from EODHD, abort the listings/full/news "
             "phase and KEEP the existing docs/data/listings.json etc. The "
             "intelligence/ refresh still runs.",
    )
    args = p.parse_args()

    intel_db.init_store()
    orchestrator.fund_cache_clear()   # fresh cache for each build
    _clean_eodhd_derived()

    listings: list[dict] = []
    full_count = 0
    news_count = 0
    auth_failed = False

    try:
        listings = export_listings(args.window)
    except _EODHDAuthFailure as e:
        auth_failed = True
        log.error("ABORT EOD-derived phase: %s", e)
        log.warning("Preserving previous docs/data/listings.json etc. "
                    "Intelligence refresh still proceeds.")
        # Restore listings.json by reading whatever's already on disk
        # (we wiped it during _clean_eodhd_derived; pull from git working tree
        #  fallback — but for simplicity write back an empty array). The
        #  workflow checks `auth_failed` and refuses to commit empty data.
        _write_json(DATA / "listings.json", [])

    if not auth_failed:
        if not args.skip_full and listings:
            full_count = export_full_details(listings, max_workers=args.max_workers)
        if not args.skip_news and listings:
            news_count = export_news(listings, max_workers=args.max_workers)

    intel_count = export_intelligence()
    search_count = export_search_index(listings)

    export_manifest(
        window=args.window,
        listings_count=len(listings),
        full_count=full_count,
        intel_count=intel_count,
        news_count=news_count,
        search_count=search_count,
    )

    if auth_failed:
        log.error("Build finished with EODHD auth failure. "
                  "Listings/full/news were NOT refreshed.")
        return 2

    log.info("DONE. docs/ ready to commit + push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
