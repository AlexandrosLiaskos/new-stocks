"""
Structured stock-intelligence schema.

This is what Claude is asked to fill per stock during a research run. Every
field is investment-relevant. Missing data is `None` / empty list — never
fabricated. The frontend renders absent fields as "—".

Persistence: SQLite (`backend/_intelligence.db`). Claude writes records via
`python -m backend.intel_write SYMBOL` reading a JSON payload from stdin.
"""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class KeyPerson(BaseModel):
    name: str
    role: str
    background: Optional[str] = None        # short bio if known


class Competitor(BaseModel):
    name: str
    note: Optional[str] = None              # one-line "vs us" comparison


class NewsItem(BaseModel):
    date: str                               # YYYY-MM-DD
    headline: str
    url: Optional[str] = None
    source: Optional[str] = None


Confidence = Literal["high", "medium", "low"]


class StockIntelligence(BaseModel):
    """One row per stock. All optional except symbol — partial records OK."""
    symbol: str
    name: Optional[str] = None
    researched_at: datetime

    # WHAT THEY DO
    one_liner: Optional[str] = None              # ≤ 200 chars
    business_model: Optional[str] = None         # 2-3 sentences
    products_services: list[str] = []
    customers: Optional[str] = None              # who buys (consumers/enterprise/gov/...)
    revenue_geography: Optional[str] = None      # where revenue comes from

    # COMPETITIVE
    competitors: list[Competitor] = []
    moat: Optional[str] = None
    market_position: Optional[Literal["leader", "challenger", "niche", "early-stage", "unclear"]] = None
    industry_trend: Optional[Literal["tailwind", "neutral", "headwind", "unclear"]] = None

    # CORPORATE
    founded: Optional[int] = None
    headquarters: Optional[str] = None
    key_people: list[KeyPerson] = []
    employees: Optional[int] = None
    notable_investors: list[str] = []            # pre-IPO backers, parent co, etc.

    # INVESTMENT VIEW (3-5 each, terse)
    bull_points: list[str] = []
    bear_points: list[str] = []
    red_flags: list[str] = []
    catalysts: list[str] = []

    # RECENT EVENTS
    recent_news: list[NewsItem] = []             # last 5-10

    # PROVENANCE
    sources: list[str] = []                      # citation URLs Claude actually consulted
    confidence: Confidence = "low"
    confidence_note: Optional[str] = None        # honest disclaimer when info is sparse


# ---- friendly label map for the frontend (kept here so backend + frontend agree)

FIELD_LABELS: dict[str, str] = {
    "one_liner": "One-liner",
    "business_model": "Business model",
    "products_services": "Products & services",
    "customers": "Customers",
    "revenue_geography": "Revenue geography",
    "competitors": "Competitors",
    "moat": "Moat",
    "market_position": "Market position",
    "industry_trend": "Industry trend",
    "founded": "Founded",
    "headquarters": "Headquarters",
    "key_people": "Key people",
    "employees": "Employees",
    "notable_investors": "Notable investors / backers",
    "bull_points": "Bull case",
    "bear_points": "Bear case",
    "red_flags": "Red flags",
    "catalysts": "Catalysts",
    "recent_news": "Recent news",
    "researched_at": "Last researched",
    "confidence": "Source confidence",
}
