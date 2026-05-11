---
description: Research stocks listed in the New Stocks app and persist structured intelligence as JSON files.
---

# /research-stocks — fill the stock-intelligence store

You are running the daily intelligence research workflow for the **New Stocks** app. Your job is to research stocks that appear in the app's IPO feed and write structured records into the `intelligence/` directory (one JSON file per stock, committed to git) so the dossier UI can display them.

## How to run

1. **Get the work list.** The backend exposes the symbols that need research:
   ```bash
   curl -s "http://127.0.0.1:8765/api/intelligence/missing?period=30d&max_age_days=7&limit=20"
   ```
   This returns up to 20 symbols whose intelligence record is missing or older than 7 days. Each entry includes `symbol`, `name`, `country`, `sector`, `industry`, `web_url`, `prospectus_url`, and a one-sentence `description` — use these as the starting point.

   If the server is not running, start it: `uvicorn backend.app:app --port 8765` (set `EODHD_API_KEY` first). Pick a smaller `limit` if you want to bound this run; pick a larger one for catch-up runs.

2. **For each symbol**, do real research. Use the tools available to you:
   - **WebSearch** — search "{name} {ticker} business model", "{name} competitors", "{name} IPO prospectus", "{name} latest news", etc.
   - **WebFetch** — pull the company website (the `web_url` field), the SEC S-1 prospectus (the `prospectus_url` field for US listings), Wikipedia entries, news articles. Always cite the URLs you actually consulted.
   - **mcp__fetch__fetch** as a fallback for sites that WebFetch struggles with.

   Spend roughly 3-5 web round-trips per stock. For tiny micro-caps with no English coverage, accept a "low confidence" record rather than fabricating.

3. **Fill the schema** below. Every field is optional except `symbol` and `researched_at`. Leave a field absent (don't invent) when you don't have evidence. Always populate `sources` with the URLs you actually opened.

4. **Persist** by piping a JSON object to the writer:
   ```bash
   echo '{...full json...}' | python -m backend.intel_write
   ```
   The CLI validates against the pydantic schema and upserts. Non-zero exit means validation failed — read the stderr, fix the JSON, retry.

5. After finishing the batch, briefly summarise: how many records you wrote, average confidence, anything notable (e.g. "5 of 20 had no English-language coverage — marked low-confidence").

## Schema (matches `backend/intel_schema.py::StockIntelligence`)

```json
{
  "symbol": "AAPL.US",                          // REQUIRED — exact EODHD format from /api/intelligence/missing
  "name": "Apple Inc",                          // optional, helpful for reading the DB
  "researched_at": "2026-05-09T14:30:00",       // ISO datetime; auto-set if absent

  "one_liner": "Designs and sells consumer electronics, software, and services worldwide.",  // ≤ 200 chars
  "business_model": "Hardware sales (iPhone, Mac, iPad, wearables) plus a fast-growing services arm (App Store, iCloud, Apple Music, Pay).",
  "products_services": ["iPhone", "Mac", "iPad", "Apple Watch", "AirPods", "App Store", "iCloud", "Apple TV+"],
  "customers": "Mainly consumers globally; growing presence in enterprise and education.",
  "revenue_geography": "Americas ~43%, Europe ~25%, Greater China ~18%, Japan ~6%, Asia-Pacific ~8%.",

  "competitors": [
    {"name": "Samsung", "note": "primary smartphone rival in unit volume"},
    {"name": "Microsoft", "note": "PC ecosystem rival, Office vs iWork"},
    {"name": "Alphabet", "note": "Android vs iOS, Search vs Spotlight"}
  ],
  "moat": "Vertically-integrated hardware/software/services lock-in, brand premium, retail footprint, App Store distribution.",
  "market_position": "leader",                  // one of: leader | challenger | niche | early-stage | unclear
  "industry_trend": "neutral",                  // one of: tailwind | neutral | headwind | unclear

  "founded": 1976,
  "headquarters": "Cupertino, California, USA",
  "key_people": [
    {"name": "Tim Cook", "role": "CEO", "background": "Joined Apple 1998, COO 2007, CEO since 2011"},
    {"name": "Luca Maestri", "role": "CFO"}
  ],
  "employees": 164000,
  "notable_investors": ["Berkshire Hathaway"],

  "bull_points": [
    "Services revenue compounding at 15%+/yr with 70%+ gross margins",
    "Vision Pro opens spatial-computing platform with first-mover advantage",
    "Massive cash pile enables aggressive buybacks and AI investments"
  ],
  "bear_points": [
    "China exposure — both for sales and for manufacturing concentration",
    "Smartphone market is mature; iPhone units flat globally",
    "Regulatory pressure on App Store fees in EU (DMA) and US"
  ],
  "red_flags": [
    "Greater China revenue declining 4 quarters in a row"
  ],
  "catalysts": [
    "iPhone AI features rollout late 2026",
    "Vision Pro v2 expected Q3 2026"
  ],

  "recent_news": [
    {"date": "2026-05-02", "headline": "Apple announces $110B buyback after Q2 earnings beat", "url": "https://...", "source": "Reuters"},
    {"date": "2026-04-18", "headline": "EU fines Apple €1.8B over App Store rules", "url": "https://...", "source": "FT"}
  ],

  "sources": [
    "https://www.apple.com/investor/",
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=320193&type=10-K",
    "https://en.wikipedia.org/wiki/Apple_Inc.",
    "https://www.reuters.com/..."
  ],
  "confidence": "high",                         // one of: high | medium | low
  "confidence_note": null                       // honest disclaimer if low/medium
}
```

## Confidence calibration

- **high**: established public company with extensive coverage (Wikipedia, multiple recent reputable news sources, SEC filings or equivalent). Most facts cross-checked.
- **medium**: limited coverage, but at least the official company site + 1-2 reputable news sources OR a SEC S-1. Some claims may rest on a single source.
- **low**: very thin public information. Set `confidence_note` to explain ("Pre-IPO Indian micro-cap; English-language coverage limited to one news article and the prospectus.").

## Rules

- **Cite, don't invent.** If you can't find a fact, leave the field absent. The frontend renders missing fields as "—" — that's the right outcome.
- **Be concise.** `one_liner` ≤ 200 chars. `business_model` 2-3 sentences. Bullet items terse. The user wants signal, not prose.
- **Investment relevance is the filter.** Skip filler corporate trivia. Bull/bear points should be specific and actionable, not generic ("good company").
- **Sources must be URLs you actually opened.** No hallucinated citations.
- **Dates use YYYY-MM-DD.** Currency-formatting handled by the frontend; just store numbers/text.

## After the batch

Print a summary of the form:
```
Researched N stocks
- M high confidence
- K medium
- J low
Notable patterns: ...
```

Done. Records will be visible in any dossier opened in the app at http://127.0.0.1:8000.
