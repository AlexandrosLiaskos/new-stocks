"""
Server-free 'missing intelligence' picker.

Diffs `docs/data/listings.json` (the static snapshot the daily GH Actions
build commits) against the local `intelligence/` directory and emits one
JSON object per stale-or-missing symbol on stdout.

Used by the `/research-stocks` slash command in headless / scheduled runs
where the FastAPI dev server isn't available. Output schema matches the
FastAPI endpoint `/api/intelligence/missing` so the skill consumes it
unchanged.

    python -m backend.list_missing                     # default: 7d staleness, no cap
    python -m backend.list_missing --max-age-days 30
    python -m backend.list_missing --limit 50
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from . import intel_store as intel_db

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "docs" / "data" / "listings.json"

_FIELDS = (
    "symbol", "name", "exchange", "country", "sector", "industry",
    "status", "list_date", "web_url", "prospectus_url", "description",
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-age-days", type=int, default=7,
                   help="Symbols researched within this window are considered fresh.")
    p.add_argument("--limit", type=int, default=0,
                   help="0 = no cap (emit everything stale).")
    p.add_argument("--sort", choices=("list_date_desc", "list_date_asc", "symbol"),
                   default="list_date_desc",
                   help="Newest IPOs first by default — important for backlog runs.")
    args = p.parse_args()

    if not LISTINGS.exists():
        print(f"error: {LISTINGS} not found — run the build first", file=sys.stderr)
        return 1

    with open(LISTINGS, encoding="utf-8") as f:
        listings = json.load(f)
    by_sym = {row["symbol"]: row for row in listings if "symbol" in row}

    intel_db.init_store()
    stale = intel_db.list_stale(list(by_sym.keys()), max_age_days=args.max_age_days)

    if args.sort == "list_date_desc":
        stale.sort(key=lambda s: (by_sym[s].get("list_date") or ""), reverse=True)
    elif args.sort == "list_date_asc":
        stale.sort(key=lambda s: (by_sym[s].get("list_date") or ""))
    else:
        stale.sort()

    if args.limit > 0:
        stale = stale[: args.limit]

    out = [{k: by_sym[s].get(k) for k in _FIELDS} for s in stale]
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"# {len(out)} symbol(s) need research "
          f"(staleness > {args.max_age_days}d)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
