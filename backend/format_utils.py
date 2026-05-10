"""
Number / currency / text formatting helpers used by the orchestrator.

Conventions:
- Currency-prefixed values use locale-agnostic symbols (USD → $, EUR → €, …)
  and 2-decimal precision unless the magnitude warrants compaction.
- Large numbers compact to K / M / B / T to keep the stat-block monospace
  rows narrow.
"""
from __future__ import annotations
import re
from typing import Iterable

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$", "EUR": "€", "GBP": "£", "GBX": "p",
    "JPY": "¥", "CNY": "¥", "HKD": "HK$", "TWD": "NT$",
    "INR": "₹", "AUD": "A$", "NZD": "NZ$", "CAD": "C$",
    "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr",
    "SGD": "S$", "KRW": "₩", "BRL": "R$", "MXN": "Mex$",
    "ZAR": "R", "RUB": "₽", "TRY": "₺", "ILS": "₪",
    "AED": "د.إ", "SAR": "﷼", "PLN": "zł", "CZK": "Kč",
    "HUF": "Ft", "THB": "฿", "IDR": "Rp", "MYR": "RM",
    "PHP": "₱", "VND": "₫",
}


def currency_symbol(code: str | None) -> str:
    return CURRENCY_SYMBOLS.get((code or "").upper(), code or "")


def fmt_money(value: float | int | None, currency: str | None = "USD",
              compact: bool = True) -> str:
    if value is None or not isinstance(value, (int, float)) or value != value:
        return "—"
    sym = currency_symbol(currency)
    a = abs(value)
    if compact:
        if a >= 1e12:
            return f"{sym}{value/1e12:.2f}T"
        if a >= 1e9:
            return f"{sym}{value/1e9:.2f}B"
        if a >= 1e6:
            return f"{sym}{value/1e6:.2f}M"
        if a >= 1e3:
            return f"{sym}{value/1e3:.2f}K"
    return f"{sym}{value:,.2f}"


def fmt_pct(value: float | None, signed: bool = False, decimals: int = 2) -> str:
    if value is None or not isinstance(value, (int, float)) or value != value:
        return "—"
    s = f"{value:+.{decimals}f}%" if signed else f"{value:.{decimals}f}%"
    return s


def fmt_int(value: float | int | None) -> str:
    if value is None or not isinstance(value, (int, float)) or value != value:
        return "—"
    return f"{int(value):,}"


def fmt_ratio(value: float | None, decimals: int = 2) -> str:
    if value is None or not isinstance(value, (int, float)) or value != value:
        return "—"
    return f"{value:.{decimals}f}"


def first_sentence(text: str | None, max_chars: int = 240) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    if len(s) > max_chars:
        s = s[: max_chars - 1].rstrip() + "…"
    return s


def size_tag(market_cap: float | None) -> str | None:
    if not market_cap or not isinstance(market_cap, (int, float)):
        return None
    if market_cap >= 200e9:
        return "Mega-cap"
    if market_cap >= 10e9:
        return "Large-cap"
    if market_cap >= 2e9:
        return "Mid-cap"
    if market_cap >= 300e6:
        return "Small-cap"
    if market_cap >= 50e6:
        return "Micro-cap"
    return "Nano-cap"


def take(d: dict | None, *keys, default=None):
    """Return the first non-None / non-empty value among `keys` in dict d."""
    if not d:
        return default
    for k in keys:
        v = d.get(k)
        if v not in (None, "", 0):
            return v
    return default


def join_words(items: Iterable[str | None]) -> str:
    return " · ".join(s for s in items if s)
