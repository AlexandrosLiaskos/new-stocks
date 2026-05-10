"""
Plan-capability probe.

Detects at server startup which EODHD endpoints the active API token can
actually reach. The Fundamentals Data Feed tier (€59.99) covers IPO calendar,
fundamentals, search, exchanges, and 15-min-delayed quotes — but NOT EOD
historical OHLCV (`/api/eod/{symbol}`), which is a separate product.

Knowing this once at startup lets the frontend hide chart range pills,
the chart panel, and CSV download buttons cleanly instead of letting the
user click into broken features. We probe one cheap call against a known-
good ticker (AAPL.US, ~5 days of data) and flip a flag.

If the user upgrades their plan, restart the server — the probe re-runs.
"""
from __future__ import annotations
import datetime as dt
import logging
from typing import TypedDict
import httpx

from .eodhd.client import EODHDClient, EODHDError

log = logging.getLogger("capabilities")


class Capabilities(TypedDict):
    eod_history: bool
    live_quote: bool
    fundamentals: bool
    ipo_calendar: bool
    search: bool
    plan_hint: str


# Defaults assume the Fundamentals tier (the user's current plan).
# eod_history is the only one we actively probe; the others are baseline-true
# for Fundamentals and surface a clear error via _eodhd_error on the rare
# case they're missing (e.g. quota exhaustion, plan downgrade).
CAPS: Capabilities = {
    "eod_history": True,
    "live_quote": True,
    "fundamentals": True,
    "ipo_calendar": True,
    "search": True,
    "plan_hint": "",
}


def probe_eod_history(client: EODHDClient | None = None) -> bool:
    """One-shot probe: can we read a few days of EOD history for AAPL.US?

    Returns True on a 200 response, False on 401/403, True on transient
    errors (we don't want to penalise EODHD network blips at startup).
    """
    client = client or EODHDClient()
    today = dt.date.today()
    from_ = (today - dt.timedelta(days=5)).isoformat()
    try:
        rows = client.get("eod/AAPL.US", {"from": from_, "to": today.isoformat()})
        return bool(rows)
    except EODHDError as e:
        if e.status in (401, 403):
            return False
        log.warning("EOD probe transient failure (%s) — assuming available", e)
        return True
    except (httpx.HTTPError, Exception) as e:
        log.warning("EOD probe network failure (%s) — assuming available", e)
        return True


def run_startup_probe() -> None:
    """Populate the module-level CAPS dict. Called once at app startup."""
    eod_ok = probe_eod_history()
    CAPS["eod_history"] = eod_ok
    if not eod_ok:
        CAPS["plan_hint"] = (
            "Fundamentals Data Feed (chart + CSV require additional "
            "EOD All World subscription)"
        )
        log.info("EOD historical not in plan; chart + CSV disabled.")
    else:
        CAPS["plan_hint"] = "Full data access."
        log.info("EOD historical available; all features enabled.")
