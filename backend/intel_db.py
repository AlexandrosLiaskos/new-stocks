"""
SQLite persistence for stock intelligence records.

Single-table schema (one row per symbol). JSON columns for the list-of-objects
fields keep the access pattern simple and the file portable. Connections are
short-lived; SQLite handles concurrency fine for our single-process server.
"""
from __future__ import annotations
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from .intel_schema import StockIntelligence

DB_PATH = Path(__file__).resolve().parent.parent / "_intelligence.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intelligence (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    researched_at TEXT NOT NULL,
    one_liner TEXT,
    business_model TEXT,
    products_services TEXT,         -- JSON array of strings
    customers TEXT,
    revenue_geography TEXT,
    competitors TEXT,                -- JSON array of {name, note}
    moat TEXT,
    market_position TEXT,
    industry_trend TEXT,
    founded INTEGER,
    headquarters TEXT,
    key_people TEXT,                 -- JSON array of {name, role, background}
    employees INTEGER,
    notable_investors TEXT,          -- JSON array
    bull_points TEXT,                -- JSON array
    bear_points TEXT,                -- JSON array
    red_flags TEXT,                  -- JSON array
    catalysts TEXT,                  -- JSON array
    recent_news TEXT,                -- JSON array of {date, headline, url, source}
    sources TEXT,                    -- JSON array
    confidence TEXT NOT NULL DEFAULT 'low',
    confidence_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_researched_at ON intelligence(researched_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


# ---- serialisation helpers

_JSON_FIELDS = {
    "products_services", "competitors", "key_people", "notable_investors",
    "bull_points", "bear_points", "red_flags", "catalysts",
    "recent_news", "sources",
}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in row.keys():
        v = row[k]
        if k in _JSON_FIELDS:
            try:
                out[k] = json.loads(v) if v else []
            except (TypeError, json.JSONDecodeError):
                out[k] = []
        else:
            out[k] = v
    return out


def _record_to_columns(rec: StockIntelligence) -> dict[str, Any]:
    d = rec.model_dump(mode="json")
    for k in _JSON_FIELDS:
        d[k] = json.dumps(d.get(k) or [], ensure_ascii=False)
    return d


# ---- public API

def upsert(record: StockIntelligence) -> None:
    """Insert or update by symbol."""
    init_db()
    cols = _record_to_columns(record)
    keys = list(cols.keys())
    placeholders = ", ".join(f":{k}" for k in keys)
    columns = ", ".join(keys)
    update_clause = ", ".join(f"{k}=excluded.{k}" for k in keys if k != "symbol")
    sql = (
        f"INSERT INTO intelligence ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT(symbol) DO UPDATE SET {update_clause}"
    )
    with _connect() as conn:
        conn.execute(sql, cols)
        conn.commit()


def get(symbol: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM intelligence WHERE symbol = ?", (symbol,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_symbols() -> list[str]:
    """All symbols that already have an intelligence record."""
    init_db()
    with _connect() as conn:
        return [r[0] for r in conn.execute(
            "SELECT symbol FROM intelligence"
        ).fetchall()]


def list_stale(symbols: list[str], max_age_days: int = 7) -> list[str]:
    """Return the subset of `symbols` whose record is missing OR older
    than `max_age_days`. Used by the daily research workflow to decide
    what needs (re-)researching.
    """
    init_db()
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)).isoformat()
    fresh: set[str] = set()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT symbol FROM intelligence WHERE researched_at >= ?", (cutoff,)
        ).fetchall()
        fresh = {r[0] for r in rows}
    return [s for s in symbols if s not in fresh]


def stats() -> dict[str, int | str | None]:
    """Database overview — used by the slash command + frontend status badge."""
    init_db()
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM intelligence").fetchone()[0]
        latest = conn.execute(
            "SELECT MAX(researched_at) FROM intelligence"
        ).fetchone()[0]
    return {"total": total, "latest_researched_at": latest}
