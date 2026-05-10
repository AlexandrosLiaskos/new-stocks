"""
Orchestrator — combines EODHD primitives into our typed view models.

`build_listings()` powers the new-stocks list.
`build_full_detail()` powers the dossier.

Each builder is a pure function over EODHD payloads + format helpers.
The HTTP I/O is hidden inside the eodhd/* modules; this file is the
"shape converter" layer between those raw payloads and the frontend.
"""
from __future__ import annotations
import datetime as dt
import logging
from concurrent.futures import ThreadPoolExecutor

from . import edgar
from .eodhd import fundamentals as fnd
from .eodhd import ipos, prices, search, splits_divs
from .format_utils import (
    currency_symbol, first_sentence, fmt_int, fmt_money, fmt_pct, fmt_ratio,
    size_tag, take,
)
from .region import region_for
from .schema import (
    AnalystConsensus, DividendEvent, EarningsRow, Exchange, FinancialsCapsule,
    FinancialsRow, Holder, InsiderTrade, NewStock, OHLCRow, Region, SearchHit,
    SplitEvent, SplitsDivs, StatBlock, StockDetailFull,
)

log = logging.getLogger("orchestrator")


# ============================================================ list builder

def build_listings(*, from_: str | None = None,
                   to_: str | None = None) -> list[NewStock]:
    """Fetch raw IPO calendar for the requested window, normalise, and
    enrich every row with fundamentals + delayed quote.

    No amount cap — the period drives the size. EODHD allows 1000 req/min,
    so 16 parallel workers comfortably saturate it without 429s.
    """
    raw = ipos.fetch_ipos(from_=from_, to_=to_)
    bare = [_ipo_to_newstock(row) for row in raw]
    bare = [s for s in bare if s is not None]
    bare = sorted(bare, key=_listing_sort_key)
    if not bare:
        return []
    with ThreadPoolExecutor(max_workers=16) as ex:
        return list(ex.map(_enrich, bare))


def _ipo_to_newstock(row: dict) -> NewStock | None:
    code = (row.get("code") or "").strip()
    name = (row.get("name") or "").strip()
    if not code or not name:
        return None
    exchange = (row.get("exchange") or "").strip()
    currency = (row.get("currency") or "USD").upper()
    list_date = row.get("start_date") or None
    deal_type = row.get("deal_type")
    status = ipos.classify_status(deal_type, list_date)

    p_lo, p_hi = row.get("price_from"), row.get("price_to")
    offer = row.get("offer_price")
    if isinstance(p_lo, (int, float)) and p_lo <= 0:
        p_lo = None
    if isinstance(p_hi, (int, float)) and p_hi <= 0:
        p_hi = None
    if isinstance(offer, (int, float)) and offer <= 0:
        offer = None

    return NewStock(
        symbol=code if "." in code else f"{code}.{exchange or 'US'}",
        name=name,
        exchange=exchange or None,
        country=None,
        region=region_for(exchange, None),
        currency=currency,
        status=status,
        list_date=list_date,
        filing_date=row.get("filing_date") or None,
        amended_date=row.get("amended_date") or None,
        deal_type=deal_type,
        offer_price=offer,
        price_low=p_lo,
        price_high=p_hi,
        shares=int(row["shares"]) if row.get("shares") else None,
        tags=[],
    )


def _enrich(stock: NewStock) -> NewStock:
    """Add fundamentals + live quote to a single listing."""
    try:
        payload = fnd.fetch_fundamentals(stock.symbol)
    except Exception as e:
        log.info("fundamentals miss %s: %s", stock.symbol, e)
        payload = None

    if payload:
        gen = fnd.general(payload)
        hi = fnd.highlights(payload)
        tech = fnd.technicals(payload)

        stock.country = gen.get("CountryName") or stock.country
        stock.region = region_for(stock.exchange, stock.country)
        stock.exchange_name = gen.get("ExchangeFullName") or stock.exchange_name
        stock.sector = gen.get("Sector") or stock.sector
        stock.industry = gen.get("Industry") or stock.industry
        stock.description = first_sentence(gen.get("Description")) or stock.description
        stock.market_cap = take(hi, "MarketCapitalization", default=stock.market_cap)
        stock.employees = take(gen, "FullTimeEmployees", default=stock.employees)
        stock.web_url = gen.get("WebURL") or stock.web_url
        logo = gen.get("LogoURL")
        if logo:
            stock.logo_url = logo if logo.startswith("http") else f"https://eodhd.com{logo}"
        stock.previous_close = take(tech, "PreviousClose", default=stock.previous_close)
        if gen.get("CIK"):
            stock.prospectus_url = stock.prospectus_url or edgar.prospectus_url(gen["CIK"])

    # Live (delayed) quote for currently-trading tickers
    if stock.status == "priced":
        try:
            quote = prices.live_quote(stock.symbol)
            if quote:
                if isinstance(quote.get("close"), (int, float)) and quote["close"] > 0:
                    stock.last_price = float(quote["close"])
                if isinstance(quote.get("previousClose"), (int, float)):
                    stock.previous_close = float(quote["previousClose"])
                if isinstance(quote.get("change_p"), (int, float)):
                    stock.change_pct = float(quote["change_p"])
        except Exception as e:
            log.info("quote miss %s: %s", stock.symbol, e)

    stock.tags = _build_tags(stock)
    return stock


def _build_tags(s: NewStock) -> list[str]:
    """Categorical tags shown on the row's tag rail.

    Sector + industry give the user "what kind of business is this?"; country
    is more specific than the region pill which already exists as a filter
    (so we drop region from the tags to avoid redundancy). Size + status
    round out the at-a-glance categorisation.
    """
    tags: list[str] = []
    if s.sector:
        tags.append(s.sector)
    if s.industry and s.industry != s.sector:
        tags.append(s.industry)
    sz = size_tag(s.market_cap)
    if sz:
        tags.append(sz)
    if s.country:
        tags.append(s.country)
    tags.append(s.status.capitalize())
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _listing_sort_key(s: NewStock) -> tuple:
    rank = {"priced": 0, "upcoming": 1, "filed": 2}
    d = s.list_date or s.filing_date or "0000-00-00"
    return (rank.get(s.status, 9), -int(d.replace("-", "") or 0))


# ============================================================ detail builder

def build_full_detail(symbol: str, base: NewStock | None = None) -> StockDetailFull:
    """Build the dossier payload — runs the underlying calls in parallel."""
    payload = fnd.fetch_fundamentals(symbol)

    if base is None:
        base = _bare_from_fundamentals(symbol, payload)
        base = _enrich(base)

    stats = _stat_block(base, payload)
    fin = _financials_capsule(payload, base.currency)
    analyst = _analyst_consensus(payload, base.last_price)
    holders_list = _top_holders(payload)
    insider_list = _recent_insider(payload)
    earnings_hist, next_e = _earnings(payload)

    sd = _splits_divs(symbol, payload, base.currency)

    return StockDetailFull(
        base=base,
        stats=stats,
        financials=fin,
        analyst=analyst,
        top_holders=holders_list,
        insider_recent=insider_list,
        earnings_history=earnings_hist,
        next_earnings=next_e,
        splits_divs=sd,
    )


def _bare_from_fundamentals(symbol: str, payload: dict | None) -> NewStock:
    gen = fnd.general(payload)
    return NewStock(
        symbol=symbol,
        name=gen.get("Name") or symbol,
        exchange=gen.get("Exchange"),
        currency=gen.get("CurrencyCode") or "USD",
        country=gen.get("CountryName"),
        region=region_for(gen.get("Exchange"), gen.get("CountryName")),
        status="priced",
        list_date=gen.get("IPODate"),
    )


# ---------- stat block

def _stat_block(base: NewStock, payload: dict | None) -> list[StatBlock]:
    gen = fnd.general(payload)
    hi = fnd.highlights(payload)
    val = fnd.valuation(payload)
    tech = fnd.technicals(payload)
    cur = base.currency or "USD"
    sym = currency_symbol(cur)

    rows: list[tuple[str, str | None]] = [
        ("Symbol", base.symbol),
        ("Sector", base.sector or gen.get("Sector")),
        ("Industry", base.industry or gen.get("Industry")),
        ("Country", base.country or gen.get("CountryName")),
        ("Founded", gen.get("Founded") or gen.get("StartDate")),
        ("Employees", fmt_int(base.employees or gen.get("FullTimeEmployees"))),
        ("Market Cap", fmt_money(base.market_cap or hi.get("MarketCapitalization"), cur)),
        ("Revenue (TTM)", fmt_money(hi.get("RevenueTTM"), cur)),
        ("EBITDA", fmt_money(hi.get("EBITDA"), cur)),
        ("Profit Margin", fmt_pct((hi.get("ProfitMargin") or 0) * 100) if hi.get("ProfitMargin") is not None else "—"),
        ("ROE (TTM)", fmt_pct((hi.get("ReturnOnEquityTTM") or 0) * 100) if hi.get("ReturnOnEquityTTM") is not None else "—"),
        ("P/E (TTM)", fmt_ratio(val.get("TrailingPE") or hi.get("PERatio"))),
        ("Forward P/E", fmt_ratio(val.get("ForwardPE"))),
        ("PEG", fmt_ratio(hi.get("PEGRatio"))),
        ("Beta", fmt_ratio(tech.get("Beta"))),
        ("52W High", f"{sym}{tech['52WeekHigh']:.2f}" if isinstance(tech.get("52WeekHigh"), (int, float)) else "—"),
        ("52W Low", f"{sym}{tech['52WeekLow']:.2f}" if isinstance(tech.get("52WeekLow"), (int, float)) else "—"),
        ("Dividend Yield", fmt_pct((hi.get("DividendYield") or 0) * 100) if hi.get("DividendYield") else "—"),
        ("IPO Date", gen.get("IPODate") or base.list_date),
        ("Fiscal Year End", gen.get("FiscalYearEnd")),
    ]
    return [StatBlock(label=lbl, value=str(v)) for lbl, v in rows if v not in (None, "", "—")]


# ---------- financials capsule

_FIN_ROWS_TO_PULL: list[tuple[str, str, str, bool]] = [
    # (label, statement, key, is_currency)
    ("Revenue", "Income_Statement", "totalRevenue", True),
    ("Net Income", "Income_Statement", "netIncome", True),
    ("EBITDA", "Income_Statement", "ebitda", True),
    ("Operating Cash Flow", "Cash_Flow", "totalCashFromOperatingActivities", True),
    ("Total Assets", "Balance_Sheet", "totalAssets", True),
    ("Total Equity", "Balance_Sheet", "totalStockholderEquity", True),
]


def _financials_capsule(payload: dict | None, currency: str) -> FinancialsCapsule:
    fin = fnd.financials(payload)
    if not fin:
        return FinancialsCapsule()

    fy = fnd.general(payload).get("FiscalYearEnd")
    rep_currency = (
        ((fin.get("Income_Statement") or {}).get("currency_symbol")) or currency
    )

    yearly_keys: list[str] = []
    income_yearly = (fin.get("Income_Statement") or {}).get("yearly") or {}
    if isinstance(income_yearly, dict):
        yearly_keys = sorted(income_yearly.keys(), reverse=True)[:4]
        yearly_keys = list(reversed(yearly_keys))  # oldest → newest

    if not yearly_keys:
        return FinancialsCapsule(fiscal_year_end=fy, reporting_currency=rep_currency)

    period_labels = [k[:4] for k in yearly_keys]
    rows: list[FinancialsRow] = []

    for label, statement, key, is_currency in _FIN_ROWS_TO_PULL:
        section = (fin.get(statement) or {}).get("yearly") or {}
        values = []
        for yk in yearly_keys:
            entry = section.get(yk) or {}
            v = entry.get(key)
            try:
                v = float(v) if v not in (None, "") else None
            except (TypeError, ValueError):
                v = None
            values.append(fmt_money(v, rep_currency) if is_currency else fmt_int(v))
        if any(val != "—" for val in values):
            rows.append(FinancialsRow(label=label, period_labels=period_labels, values=values))

    # Computed margin row from Net Income / Revenue
    rev_section = (fin.get("Income_Statement") or {}).get("yearly") or {}
    margins = []
    for yk in yearly_keys:
        entry = rev_section.get(yk) or {}
        try:
            ni = float(entry.get("netIncome") or 0)
            rv = float(entry.get("totalRevenue") or 0)
            margins.append(fmt_pct(ni / rv * 100) if rv else "—")
        except (TypeError, ValueError):
            margins.append("—")
    if any(m != "—" for m in margins):
        rows.append(FinancialsRow(label="Net Margin", period_labels=period_labels, values=margins))

    return FinancialsCapsule(
        rows=rows, fiscal_year_end=fy, reporting_currency=rep_currency,
    )


# ---------- analyst consensus

def _analyst_consensus(payload: dict | None, current_price: float | None) -> AnalystConsensus:
    a = fnd.analyst_ratings(payload)
    if not a:
        return AnalystConsensus()
    rating = a.get("Rating")
    target = a.get("TargetPrice")
    pct = None
    if isinstance(target, (int, float)) and current_price and current_price > 0:
        pct = (target - current_price) / current_price * 100.0
    return AnalystConsensus(
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        target_price=float(target) if isinstance(target, (int, float)) else None,
        target_pct_vs_current=pct,
        strong_buy=int(a.get("StrongBuy") or 0),
        buy=int(a.get("Buy") or 0),
        hold=int(a.get("Hold") or 0),
        sell=int(a.get("Sell") or 0),
        strong_sell=int(a.get("StrongSell") or 0),
    )


# ---------- holders

def _top_holders(payload: dict | None, max_rows: int = 10) -> list[Holder]:
    h = fnd.holders(payload)
    inst = h.get("Institutions") or {}
    if not isinstance(inst, dict):
        return []
    out: list[Holder] = []
    for k, v in sorted(inst.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999):
        if not isinstance(v, dict):
            continue
        out.append(Holder(
            rank=len(out) + 1,
            name=v.get("name") or "—",
            pct=float(v["totalShares"]) if isinstance(v.get("totalShares"), (int, float)) else None,
            change_pct=float(v["change_p"]) if isinstance(v.get("change_p"), (int, float)) else None,
            date=v.get("date"),
        ))
        if len(out) >= max_rows:
            break
    return out


# ---------- insider transactions

def _recent_insider(payload: dict | None, max_rows: int = 10) -> list[InsiderTrade]:
    it = fnd.insider_transactions(payload)
    if not isinstance(it, dict):
        return []
    rows = []
    for k, v in it.items():
        if not isinstance(v, dict):
            continue
        rows.append(v)
    rows.sort(key=lambda x: x.get("transactionDate") or x.get("date") or "", reverse=True)
    out: list[InsiderTrade] = []
    for v in rows[:max_rows]:
        side = None
        ad = (v.get("transactionAcquiredDisposed") or "").upper()
        if ad == "A":
            side = "BUY"
        elif ad == "D":
            side = "SELL"
        out.append(InsiderTrade(
            date=v.get("transactionDate") or v.get("date") or "",
            owner=v.get("ownerName") or "—",
            code=v.get("transactionCode"),
            side=side,
            amount=int(v["transactionAmount"]) if isinstance(v.get("transactionAmount"), (int, float)) else None,
            price=float(v["transactionPrice"]) if isinstance(v.get("transactionPrice"), (int, float)) else None,
            sec_link=v.get("secLink"),
        ))
    return out


# ---------- earnings

def _earnings(payload: dict | None) -> tuple[list[EarningsRow], EarningsRow | None]:
    e = fnd.earnings(payload)
    if not e:
        return [], None
    history_src = e.get("History") or {}
    rows = []
    for key, v in history_src.items():
        if not isinstance(v, dict):
            continue
        rows.append(EarningsRow(
            period=str(key),
            report_date=v.get("reportDate"),
            actual=float(v["epsActual"]) if isinstance(v.get("epsActual"), (int, float)) else None,
            estimate=float(v["epsEstimate"]) if isinstance(v.get("epsEstimate"), (int, float)) else None,
            surprise_pct=float(v["surprisePercent"]) if isinstance(v.get("surprisePercent"), (int, float)) else None,
            timing=v.get("beforeAfterMarket"),
        ))
    rows.sort(key=lambda r: r.period, reverse=True)

    today_iso = dt.date.today().isoformat()
    past = [r for r in rows if (r.report_date or r.period) <= today_iso][:6]

    # Next scheduled earnings — from Trend section if available
    nxt_src = (e.get("Trend") or {})
    next_e = None
    for key, v in nxt_src.items():
        if not isinstance(v, dict):
            continue
        rd = v.get("date") or v.get("reportDate")
        if rd and rd > today_iso:
            next_e = EarningsRow(period=str(key), report_date=rd, timing=v.get("beforeAfterMarket"))
            break

    return past, next_e


# ---------- splits / dividends

def _splits_divs(symbol: str, payload: dict | None, currency: str) -> SplitsDivs:
    sd_block = fnd.splits_dividends(payload)

    # Splits — try the dedicated endpoint first (cleaner), fall back to fundamentals payload
    splits_out: list[SplitEvent] = []
    try:
        for row in (splits_divs.fetch_splits(symbol) or [])[:5]:
            d = row.get("date")
            r = row.get("split")
            if d and r:
                splits_out.append(SplitEvent(date=d, ratio=str(r)))
    except Exception:
        pass
    if not splits_out and isinstance(sd_block, dict) and sd_block.get("LastSplitDate"):
        splits_out.append(SplitEvent(
            date=sd_block["LastSplitDate"],
            ratio=str(sd_block.get("LastSplitFactor") or "—"),
        ))

    # Dividends — last 8
    divs_out: list[DividendEvent] = []
    try:
        rows = splits_divs.fetch_dividends(symbol) or []
        rows.sort(key=lambda r: r.get("date") or "", reverse=True)
        for row in rows[:8]:
            d = row.get("date")
            v = row.get("value") or row.get("dividend") or row.get("amount")
            if d and isinstance(v, (int, float)):
                divs_out.append(DividendEvent(date=d, amount=float(v), currency=currency))
    except Exception:
        pass

    return SplitsDivs(splits=splits_out, dividends=divs_out)


# ============================================================ history

def history_rows(symbol: str, range_: str) -> list[OHLCRow]:
    rows = prices.history_for_range(symbol, range_)
    out: list[OHLCRow] = []
    for r in rows:
        try:
            out.append(OHLCRow(
                t=str(r.get("date") or r.get("Date")),
                o=float(r.get("open") or 0),
                h=float(r.get("high") or 0),
                l=float(r.get("low") or 0),
                c=float(r.get("close") or 0),
                v=float(r.get("volume") or 0),
            ))
        except (TypeError, ValueError):
            continue
    return out


# ============================================================ search

def search_hits(query: str) -> list[SearchHit]:
    raw = search.search(query)
    out: list[SearchHit] = []
    for row in raw:
        code = (row.get("Code") or "").strip()
        ex = (row.get("Exchange") or "").strip()
        if not code:
            continue
        sym = code if "." in code else (f"{code}.{ex}" if ex else code)
        out.append(SearchHit(
            symbol=sym,
            name=row.get("Name") or code,
            exchange=ex or None,
            country=row.get("Country") or None,
            type=row.get("Type") or None,
            currency=row.get("Currency") or None,
        ))
    return out


# ============================================================ exchanges

def exchanges_list() -> list[Exchange]:
    from .eodhd.exchanges import list_exchanges
    out: list[Exchange] = []
    for row in list_exchanges():
        code = row.get("Code") or row.get("OperatingMIC") or ""
        if not code:
            continue
        out.append(Exchange(
            code=code,
            name=row.get("Name") or code,
            country=row.get("Country") or None,
            currency=row.get("Currency") or None,
            region=region_for(code, row.get("Country")),
        ))
    return out
