"""
Tiny EDGAR helper — produces an SEC prospectus URL from an EODHD CIK.

EDGAR is free and authoritative; we use it only to give US listings a
"Prospectus → SEC" link in the dossier. No fundamentals or price data.
"""
from __future__ import annotations


def prospectus_url(cik: str | int | None) -> str | None:
    if not cik:
        return None
    cik_str = str(cik).lstrip("0") or "0"
    return (
        f"https://www.sec.gov/cgi-bin/browse-edgar?"
        f"action=getcompany&CIK={cik_str}&type=S-1&dateb=&owner=include&count=10"
    )
