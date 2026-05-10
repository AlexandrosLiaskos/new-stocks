"""Batch-write low-research stubs (ETFs, SPACs, delisted) so they don't
reappear in /api/intelligence/missing every day.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOW = dt.datetime.now(dt.timezone.utc).isoformat()

STUBS = [
    # (symbol, name, kind, one_liner, note)
    ("MOBI.US",  "Sky-mobi Ltd (ADR)",                              "delisted",
     "Delisted Chinese mobile-app store ADR; no longer trading.",
     "Listed in EODHD calendar but already delisted; no active investment thesis."),
    ("SAGUU.US", "Shreya Acquisition Group Unit",                   "spac",
     "SPAC unit (no operating business). Listing exists to identify and merge with a target company.",
     "SPAC pre-deal — research deferred until a target is announced."),
    ("KMCA.US",  "Exchange Listed Funds Trust",                     "etf",
     "Listed as an ETF/trust vehicle, not an operating company.",
     "ETF/trust — investment thesis is the underlying basket, not the issuer."),
    ("BUYB.US",  "ProShares Trust",                                 "etf",
     "ProShares-issued ETF tracking a buyback / shareholder-yield strategy.",
     "ETF — investment thesis lives in the index methodology, not company-level research."),
    ("WARP.US",  "VanEck Space ETF",                                "etf",
     "VanEck thematic ETF holding companies in the space economy (launch, satellites, defence space).",
     "ETF — investment thesis is the space-economy theme + holding methodology."),
    ("TCAN.US",  "21Shares Canton Network ETF",                     "etf",
     "21Shares ETF tied to Canton Network (tokenised-asset blockchain) ecosystem.",
     "ETF — investment thesis is the Canton Network / institutional-tokenisation theme."),
    ("REA.US",   "Rydex 2x S&P Select Sector Energy ETF",           "etf",
     "Leveraged 2x ETF tracking the S&P Select Sector Energy index.",
     "Leveraged ETF — designed for short-term tactical exposure, not buy-and-hold."),
    ("VECAU.US", "Vernal Capital Acquisition Corp Unit",            "spac",
     "SPAC unit. No operating business until merger target is announced.",
     "SPAC pre-deal — research deferred until a target is announced."),
    ("DUSG.US",  "U.S. Small Cap Growth Portfolio: ETF Class",      "etf",
     "ETF share class of a US small-cap growth strategy.",
     "ETF — investment thesis is the small-cap-growth basket, not company-level research."),
    ("CLOO.US",  "New York Life Investments Active ETF Trust",      "etf",
     "Active ETF issued under the New York Life Investments umbrella.",
     "ETF — investment thesis is the manager's active-strategy mandate."),
    ("NICO.US",  "Series Portfolios Trust",                         "etf",
     "ETF/series trust vehicle; not an operating company.",
     "ETF/trust — investment thesis lives in the underlying portfolio."),
    ("PCEB.US",  "FundVantage Trust",                               "etf",
     "ETF series trust managed by FundVantage; not an operating company.",
     "ETF/trust — investment thesis lives in the underlying portfolio."),
    ("SKAIU.US", "Sky Acquisition Group Unit",                      "spac",
     "SPAC unit. No operating business until merger target is announced.",
     "SPAC pre-deal — research deferred until a target is announced."),
    ("PONOR.US", "Pono Capital Four, Inc. Rights",                  "spac",
     "Rights warrant tied to Pono Capital Four SPAC. Pre-deal SPAC derivative.",
     "SPAC rights — research deferred until a target is announced."),
]


def main() -> None:
    written, failed = 0, 0
    for sym, name, kind, one_liner, note in STUBS:
        record = {
            "symbol": sym,
            "name": name,
            "researched_at": NOW,
            "one_liner": one_liner,
            "products_services": [],
            "competitors": [],
            "key_people": [],
            "notable_investors": [],
            "bull_points": [],
            "bear_points": [],
            "red_flags": [],
            "catalysts": [],
            "recent_news": [],
            "sources": [],
            "confidence": "low",
            "confidence_note": note,
        }
        proc = subprocess.run(
            [sys.executable, "-m", "backend.intel_write"],
            input=json.dumps(record),
            text=True, capture_output=True, cwd=ROOT,
        )
        if proc.returncode == 0:
            written += 1
            print(proc.stdout.strip())
        else:
            failed += 1
            print(f"FAIL {sym}: {proc.stderr.strip()}", file=sys.stderr)
    print(f"\nstubs: {written} written, {failed} failed")


if __name__ == "__main__":
    main()
