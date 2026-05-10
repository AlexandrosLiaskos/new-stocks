"""
Pydantic models for the New Stocks app.

Single source of truth for the JSON shape exchanged between backend and
frontend. Every field has an explicit type; optional fields use `None`
defaults so the frontend can render placeholders consistently.
"""
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------ enums

Status = Literal["priced", "upcoming", "filed"]


class Region(str, Enum):
    US = "US"
    UK = "UK"
    EU = "EU"
    ASIA = "ASIA"
    INDIA = "INDIA"
    OCEANIA = "OCEANIA"
    AFRICA = "AFRICA"
    LATAM = "LATAM"
    OTHER = "OTHER"


# ------------------------------------------------------------------ list row

class NewStock(BaseModel):
    """One row in the new-listings list — also the base for the dossier."""
    model_config = ConfigDict(use_enum_values=True)

    # Identity
    symbol: str                    # EODHD format: AAPL.US, RELIANCE.NSE
    name: str
    exchange: Optional[str] = None         # short code
    exchange_name: Optional[str] = None    # full name
    country: Optional[str] = None
    region: Region = Region.OTHER
    currency: str = "USD"

    # IPO state
    status: Status = "priced"
    list_date: Optional[str] = None
    filing_date: Optional[str] = None
    amended_date: Optional[str] = None
    deal_type: Optional[str] = None        # "Expected" / "Priced"
    offer_price: Optional[float] = None
    price_low: Optional[float] = None
    price_high: Optional[float] = None
    shares: Optional[int] = None

    # Live data (delayed)
    last_price: Optional[float] = None
    previous_close: Optional[float] = None
    change_pct: Optional[float] = None

    # Profile
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    market_cap: Optional[float] = None
    employees: Optional[int] = None
    web_url: Optional[str] = None
    logo_url: Optional[str] = None

    # Tags surfaced in the row
    tags: list[str] = []

    # Provenance
    prospectus_url: Optional[str] = None


# ------------------------------------------------------------------ dossier

class StatBlock(BaseModel):
    label: str
    value: str


class FinancialsRow(BaseModel):
    """One labelled row in the financials capsule (Revenue, EBITDA, etc.)."""
    label: str
    period_labels: list[str]    # ["2022", "2023", "2024", "TTM"]
    values: list[str]           # already formatted, monospace-ready


class FinancialsCapsule(BaseModel):
    rows: list[FinancialsRow] = []
    fiscal_year_end: Optional[str] = None
    reporting_currency: Optional[str] = None


class AnalystConsensus(BaseModel):
    rating: Optional[float] = None              # 1.0 .. 5.0
    target_price: Optional[float] = None
    target_pct_vs_current: Optional[float] = None
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0


class Holder(BaseModel):
    rank: int
    name: str
    pct: Optional[float] = None
    change_pct: Optional[float] = None
    date: Optional[str] = None


class InsiderTrade(BaseModel):
    date: str
    owner: str
    code: Optional[str] = None      # SEC transaction code (P, S, A, ...)
    side: Optional[str] = None      # BUY | SELL | OTHER
    amount: Optional[int] = None    # shares
    price: Optional[float] = None
    sec_link: Optional[str] = None


class EarningsRow(BaseModel):
    period: str                     # YYYY-Q# or report date
    report_date: Optional[str] = None
    actual: Optional[float] = None
    estimate: Optional[float] = None
    surprise_pct: Optional[float] = None
    timing: Optional[str] = None    # BeforeMarket / AfterMarket / null


class SplitEvent(BaseModel):
    date: str
    ratio: str       # "4:1"


class DividendEvent(BaseModel):
    date: str
    amount: float
    currency: Optional[str] = None


class SplitsDivs(BaseModel):
    splits: list[SplitEvent] = []
    dividends: list[DividendEvent] = []


class StockDetailFull(BaseModel):
    base: NewStock
    stats: list[StatBlock] = []
    financials: FinancialsCapsule = FinancialsCapsule()
    analyst: AnalystConsensus = AnalystConsensus()
    top_holders: list[Holder] = []
    insider_recent: list[InsiderTrade] = []
    earnings_history: list[EarningsRow] = []
    next_earnings: Optional[EarningsRow] = None
    splits_divs: SplitsDivs = SplitsDivs()


# ------------------------------------------------------------------ history / search / exchange

class OHLCRow(BaseModel):
    t: str
    o: float
    h: float
    l: float
    c: float
    v: float


class SearchHit(BaseModel):
    symbol: str           # EODHD format
    name: str
    exchange: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None     # "Common Stock", "ETF", ...
    currency: Optional[str] = None


class Exchange(BaseModel):
    code: str             # NASDAQ, LSE, NSE, ...
    name: str
    country: Optional[str] = None
    currency: Optional[str] = None
    region: Region = Region.OTHER
