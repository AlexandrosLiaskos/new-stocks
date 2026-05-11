"""
Filesystem-backed stock-intelligence store.

One JSON file per stock under `intelligence/{SYMBOL}.json` (repo root).
The directory IS the source of truth — committed to git, diff-friendly,
no binary database, every change shows which stock moved.

Replaces the previous SQLite-backed `intel_db` module. The public API
(get / upsert / list_symbols / list_stale / stats) is unchanged so
callers don't notice the swap.

The build script copies these files into `docs/data/intelligence/` at
build time so the static site serves them. Direct edits or `/research-
stocks` writes happen against the source dir; the build never deletes
or rewrites them — research and IPO-calendar refreshes are independent.
"""
from __future__ import annotations
import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Any

from .intel_schema import StockIntelligence

log = logging.getLogger("intel_store")

# Source-of-truth directory — committed to git.
STORE_DIR = Path(__file__).resolve().parent.parent / "intelligence"


def _safe_filename(symbol: str) -> str:
    """Same convention as build_static — symbols with slashes are rejected."""
    if not re.fullmatch(r"[A-Za-z0-9.\-_]+", symbol):
        raise ValueError(f"unsafe symbol for filename: {symbol!r}")
    return symbol


def _path_for(symbol: str) -> Path:
    return STORE_DIR / f"{_safe_filename(symbol)}.json"


def init_store() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------- public API

def upsert(record: StockIntelligence) -> Path:
    """Atomic write of a single record. Returns the target path."""
    init_store()
    target = _path_for(record.symbol)
    tmp = target.with_suffix(".json.tmp")
    payload = record.model_dump(mode="json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(target)
    return target


def get(symbol: str) -> dict[str, Any] | None:
    p = _path_for(symbol)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("intel: failed to read %s: %s", p, e)
        return None


def list_symbols() -> list[str]:
    if not STORE_DIR.exists():
        return []
    return sorted(p.stem for p in STORE_DIR.glob("*.json"))


def list_stale(symbols: list[str], max_age_days: int = 7) -> list[str]:
    """Return the subset of `symbols` whose record is missing OR older
    than `max_age_days`. Uses each record's `researched_at` field rather
    than file mtime (mtime gets clobbered by git checkout).
    """
    cutoff_iso = (dt.datetime.now(dt.timezone.utc)
                  - dt.timedelta(days=max_age_days)).isoformat()
    fresh: set[str] = set()
    for sym in symbols:
        rec = get(sym)
        if rec and rec.get("researched_at", "0000") >= cutoff_iso:
            fresh.add(sym)
    return [s for s in symbols if s not in fresh]


def stats() -> dict[str, Any]:
    syms = list_symbols()
    latest = None
    for s in syms:
        rec = get(s) or {}
        ts = rec.get("researched_at")
        if ts and (latest is None or ts > latest):
            latest = ts
    return {"total": len(syms), "latest_researched_at": latest}


# Backwards-compat shim — old callers may still call `init_db()`.
init_db = init_store
