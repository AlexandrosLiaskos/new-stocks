# New Stocks

A daily-refreshed feed of newly listed stocks worldwide — IPOs, direct listings, SPACs, and the upcoming pipeline. Each entry comes with a structured business-intelligence dossier (one-liner, business model, competitors, key people, bull/bear/red-flag/catalyst points, recent news).

The site is **fully static**. All data is baked into JSON files at build time and served via GitHub Pages — no backend, no API key in the browser, no live API calls from the page.

```
docs/                      ← served by GitHub Pages
├── index.html             pure HTML/CSS/JS, no build step
├── styles.css, styles-sections.css
├── app.js, sections.js, search.js
└── data/
    ├── manifest.json      build timestamp + counts
    ├── listings.json      enriched IPO calendar (one bundle)
    ├── search.json        client-side search index
    ├── full/{SYMBOL}.json per-stock dossier
    └── intelligence/{SYMBOL}.json
                           per-stock structured intelligence
```

## How it stays fresh

1. **EODHD Fundamentals API** (€59.99/mo) provides the global IPO calendar + per-stock fundamentals.
2. **`/research-stocks`** Claude Code slash command researches each stock (web search + fetch) and writes structured records into `_intelligence.db` (SQLite).
3. **`python -m backend.build_static`** reads EODHD live + the SQLite database and writes the JSON snapshot into `docs/data/`.
4. **GitHub Actions** (`.github/workflows/deploy.yml`) runs the build daily and pushes the refreshed snapshot. GitHub Pages serves it.

## One-time GitHub Pages setup

1. Push this repo to GitHub.
2. **Settings → Pages**: source = *GitHub Actions*.
3. **Settings → Secrets and variables → Actions**: add a secret named `EODHD_API_KEY` with your EODHD token.
4. The `Build & deploy` workflow runs on every push to `main`, daily at 03:30 UTC, and on manual dispatch.

## Running it locally

```bash
pip install -r requirements.txt
export EODHD_API_KEY=your_key                 # bash / WSL
$env:EODHD_API_KEY = "your_key"               # PowerShell

# 1. Research the missing stocks (in Claude Code)
#    /research-stocks                         ← slash command in this repo
#
# 2. Build the static snapshot
python -m backend.build_static --window 1y

# 3. Preview docs/ locally
python -m http.server -d docs 8000
# → open http://localhost:8000
```

`build_static` flags:
- `--window` — `30d` | `90d` | `6m` | `1y` (default) | `all` — how far back to pull the IPO calendar.
- `--skip-full` — skip per-symbol dossier export. Faster but the modal is empty.
- `--max-workers N` — parallel EODHD calls (default 12).

## Layout (full)

```
backend/
├── app.py                FastAPI app — used in dev for /research-stocks helpers
├── build_static.py       static-site exporter (writes docs/data/)
├── orchestrator.py       turns EODHD payloads into typed view models
├── schema.py             pydantic models (NewStock, StockDetailFull, ...)
├── intel_schema.py       StockIntelligence model
├── intel_db.py           SQLite read/write helpers
├── intel_write.py        CLI used by Claude Code to upsert records
├── cache.py              diskcache TTL wrapper (used in dev)
├── capabilities.py       runtime EOD-availability probe (dev only)
├── format_utils.py       money/pct/text formatters
├── region.py             exchange/country → Region enum
├── edgar.py              SEC prospectus URL helper
└── eodhd/                typed EODHD client + per-endpoint modules

docs/                     GitHub Pages root (committed)
frontend/                 dev-only legacy frontend (drives the FastAPI app)
.claude/commands/research-stocks.md   slash command for Claude Code
.github/workflows/deploy.yml          daily build + deploy
_intelligence.db          SQLite — committed so the build is reproducible
```

## Daily workflow (manual)

```bash
# 1. Open Claude Code in this repo.
# 2. Run the slash command:
/research-stocks

# 3. Build the snapshot:
python -m backend.build_static --window 1y

# 4. Commit + push:
git add _intelligence.db docs/
git commit -m "data: refresh $(date -u +%Y-%m-%d)"
git push
```

GitHub Pages picks up the new `docs/` automatically.

## Visual register

Editorial classicism: monochrome surfaces, hairline rules instead of containers, EB Garamond serif for narrative voice, JetBrains Mono for numerical values, Inter for UI mechanics. No card chrome, no shadows, no gradients, no rounded corners outside the dossier overlay.
