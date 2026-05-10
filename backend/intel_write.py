"""
CLI entry point for Claude Code (or any caller) to upsert one intelligence
record into SQLite.

Usage:
    # JSON via stdin
    echo '{"symbol":"AAPL.US",...}' | python -m backend.intel_write
    # JSON via --file
    python -m backend.intel_write --file path/to/record.json

The JSON must conform to `StockIntelligence`. Any unknown / extra fields are
rejected (pydantic strict mode). `researched_at` is auto-set to now if not
supplied.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import sys

from pydantic import ValidationError

from .intel_db import upsert
from .intel_schema import StockIntelligence


def _load_payload(file: str | None) -> dict:
    if file:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("error: no JSON on stdin (or pass --file <path>)")
    return json.loads(raw)


def main() -> int:
    p = argparse.ArgumentParser(description="Upsert a stock-intelligence record into SQLite.")
    p.add_argument("--file", help="Path to a JSON file (otherwise reads stdin).")
    args = p.parse_args()

    try:
        payload = _load_payload(args.file)
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON ({e})", file=sys.stderr)
        return 2

    payload.setdefault("researched_at", dt.datetime.now(dt.timezone.utc).isoformat())

    try:
        rec = StockIntelligence.model_validate(payload)
    except ValidationError as e:
        print("error: validation failed", file=sys.stderr)
        print(e.json(indent=2), file=sys.stderr)
        return 3

    upsert(rec)
    print(f"ok: {rec.symbol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
