"""Write the 6 researched intelligence records (operating companies)."""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = dt.datetime.now(dt.timezone.utc).isoformat()


RECORDS = [
    # ========================================================== ODTX.US
    {
        "symbol": "ODTX.US",
        "name": "Odyssey Therapeutics, Inc.",
        "researched_at": NOW,
        "one_liner": "Clinical-stage immunology biotech developing precision-targeted small molecules for autoimmune and inflammatory diseases.",
        "business_model": "Pre-revenue R&D model — fund a portfolio of immunology programmes through clinical trials, then commercialise the winners or partner with large pharma. Lead asset OD-001 is a RIPK2 scaffolding inhibitor in mid-stage development for ulcerative colitis.",
        "products_services": [
            "OD-001 — RIPK2 scaffolding inhibitor, Phase 2 in ulcerative colitis (lead asset)",
            "Pipeline programs in atopic dermatitis, COPD, and B-cell-mediated autoimmunity (lupus)",
            "Five additional preclinical immunology programmes"
        ],
        "customers": "Pre-commercial; future customers are gastroenterologists, rheumatologists, and pulmonologists prescribing for autoimmune/inflammatory disease.",
        "revenue_geography": "No commercial revenue yet — proceeds from IPO + private placement fund clinical trials globally.",
        "competitors": [
            {"name": "AbbVie (Skyrizi, Rinvoq)", "note": "incumbent IL-23 / JAK leader in IBD"},
            {"name": "Takeda (Entyvio)", "note": "integrin blocker; Odyssey is running a combination study with Entyvio"},
            {"name": "Eli Lilly (Omvoh)", "note": "IL-23 entrant in ulcerative colitis"},
            {"name": "TL1A-targeting biotechs (Prometheus, Roivant)", "note": "alternative novel-mechanism IBD drug class attracting attention"},
            {"name": "Pfizer (etrasimod)", "note": "S1P1 modulator in ulcerative colitis"}
        ],
        "moat": "RIPK2 scaffolding inhibition is a relatively unexplored mechanism of action — most pharma RIPK efforts focused on RIPK1 with limited success. Differentiated science backed by experienced founder and well-capitalised investor base.",
        "market_position": "early-stage",
        "industry_trend": "tailwind",
        "founded": 2021,
        "headquarters": "Boston / Cambridge, Massachusetts area, USA",
        "key_people": [
            {"name": "Gary Glick", "role": "Founder & CEO", "background": "Biotech veteran; founder of multiple drug startups subsequently acquired."}
        ],
        "employees": None,
        "notable_investors": [
            "OrbiMed (early lead)",
            "SR One",
            "TPG Life Sciences Innovations (concurrent IPO private placement)"
        ],
        "bull_points": [
            "$304M raised at IPO (15.5M shares at $18) — debut closed +11%; signals biotech-IPO appetite returning",
            "Differentiated RIPK2 mechanism vs the crowded IL-23/JAK/integrin space",
            "Combination trial with Takeda's Entyvio gives a credible large-pharma validation pathway",
            "$727M in venture funding pre-IPO + IPO proceeds — substantial cash runway for Phase 2/3",
            "Pipeline diversification across IBD, atopic dermatitis, COPD, lupus reduces single-asset risk"
        ],
        "bear_points": [
            "Pre-revenue clinical-stage biotech — binary trial outcomes; full pipeline failure is possible",
            "Second IPO attempt (first abandoned June 2025) — market debut already partially digested",
            "RIPK2 scaffolding is unproven in late-stage trials industry-wide",
            "Five of six pipeline programmes have not yet entered human testing",
            "IBD biologics market is crowded with entrenched competitors (AbbVie, Takeda, Lilly)"
        ],
        "red_flags": [
            "Prior IPO attempt withdrawn 2025 — markets had concerns the first time around"
        ],
        "catalysts": [
            "OD-001 Phase 2 ulcerative colitis monotherapy readouts",
            "OD-001 + Entyvio combination study initiation (later 2026)",
            "First-in-human Phase 1 for B-cell autoimmunity programme (planned next year)",
            "Atopic dermatitis or COPD programme IND filings"
        ],
        "recent_news": [
            {"date": "2026-05-08", "headline": "Odyssey Therapeutics jumps 11% in Nasdaq debut after $304M IPO", "url": "https://www.bloomberg.com/news/articles/2026-05-08/odyssey-therapeutics-climbs-11-after-304-million-us-ipo", "source": "Bloomberg"},
            {"date": "2026-05-08", "headline": "Odyssey CEO Glick sees $304M IPO creating 'little large pharma'", "url": "https://www.fiercebiotech.com/biotech/odyssey-voyages-nasdaq-304m-ipo-fund-autoimmune-inflammatory-pipeline", "source": "FierceBiotech"},
            {"date": "2026-05-08", "headline": "Odyssey prices upsized $304M IPO + private placement", "url": "https://www.globenewswire.com/news-release/2026/05/08/3290782/0/en/odyssey-therapeutics-announces-pricing-of-upsized-initial-public-offering.html", "source": "GlobeNewswire"},
            {"date": "2026-05-08", "headline": "ODTX prices at $18, raises $304M", "url": "https://www.heygotrade.com/en/news/odyssey-therapeutics-odtx-ipo-prices-18-raises-304m/", "source": "HeyGoTrade"}
        ],
        "sources": [
            "https://odysseytx.com/pipeline/",
            "https://www.bloomberg.com/news/articles/2026-05-08/odyssey-therapeutics-climbs-11-after-304-million-us-ipo",
            "https://www.fiercebiotech.com/biotech/odyssey-voyages-nasdaq-304m-ipo-fund-autoimmune-inflammatory-pipeline",
            "https://medcitynews.com/2026/05/odyssey-therapeutics-ipo-gary-glick-ulcerative-colitis-immunology-inflammation-ibd-odtx/",
            "https://www.biopharmadive.com/news/odyssey-ipo-price-biotech-gary-glick-immune-drugs/819465/",
            "https://stockanalysis.com/stocks/odtx/"
        ],
        "confidence": "high",
        "confidence_note": None,
    },
    # ========================================================== SUJA.US
    {
        "symbol": "SUJA.US",
        "name": "Suja Life, Inc.",
        "researched_at": NOW,
        "one_liner": "Better-for-you beverage platform: organic cold-pressed juices, wellness shots, and functional low-sugar sodas (Suja Organic, Vive Organic, Slice).",
        "business_model": "Vertically integrated CPG: in-house 270k sq-ft Oceanside CA manufacturing + cold-chain distribution to 37,000+ retail doors. Sells through grocery (Whole Foods, Costco, Target, Kroger) and e-commerce. High-pressure-processing (HPP) tech extends shelf life without preservatives.",
        "products_services": [
            "Suja Organic — flagship organic cold-pressed juice line",
            "Vive Organic — wellness shots (immunity, detox, energy)",
            "Slice — reimagined low-sugar functional soda",
            "Mid-day-pickup category: probiotic, gut-health, and protein drinks"
        ],
        "customers": "US health-conscious consumers via mass and natural-grocery channels (Whole Foods, Sprouts, Kroger, Target, Costco) plus DTC.",
        "revenue_geography": "Predominantly US.",
        "competitors": [
            {"name": "PepsiCo (Naked Juice, Tropicana, Olipop investments)", "note": "incumbent ad-spend giant in juice + functional beverage"},
            {"name": "Coca-Cola (Odwalla, Simply, fairlife, BodyArmor)", "note": "vast distribution + better-for-you portfolio"},
            {"name": "Hain Celestial", "note": "organic-leaning portfolio overlap"},
            {"name": "Zevia", "note": "leading low-sugar / zero-sugar soda direct competitor"},
            {"name": "Olipop / Poppi", "note": "fast-growing functional-soda competitors in Slice's category"}
        ],
        "moat": "47% market share in US cold-pressed juice + 42% in wellness shots; vertically integrated cold-chain + HPP tech with 99% fill rate is hard for smaller competitors to replicate.",
        "market_position": "leader",
        "industry_trend": "tailwind",
        "founded": 2012,
        "headquarters": "Oceanside, California, USA",
        "key_people": [],
        "employees": None,
        "notable_investors": [],
        "bull_points": [
            "47% US cold-pressed juice market share + 42% wellness-shot share — category leader",
            "$327M revenue 2025, +26.1% YoY — strong growth in a slowing CPG environment",
            "Vertically integrated with 270k sq-ft HPP plant and 37k+ retail doors — operational moat",
            "Riding the functional-beverage / better-for-you tailwind alongside Olipop/Poppi/Zevia",
            "Slice expansion into reimagined-soda category opens incremental TAM"
        ],
        "bear_points": [
            "Net loss of $23.3M in 2025 — profitability not yet achieved at scale",
            "Heavy competition from Pepsi/Coca-Cola who own distribution and shelf space",
            "Cold-chain logistics is capital-intensive; margin pressure if expansion outpaces efficiency",
            "Consumer trade-down risk if US recession bites premium organic beverages",
            "Better-for-you category attracting a flood of new entrants — share defence cost rising"
        ],
        "red_flags": [
            "Persistent operating losses; path to profitability not yet demonstrated"
        ],
        "catalysts": [
            "Slice national distribution rollout",
            "Costco / Walmart placement expansion",
            "First profitable quarter would re-rate the multiple sharply",
            "Potential acquisition target for Coca-Cola, PepsiCo, or Keurig Dr Pepper"
        ],
        "recent_news": [
            {"date": "2026-04-27", "headline": "Suja Life launches IPO roadshow on functional-beverage boom", "url": "https://briefglance.com/articles/suja-life-launches-ipo-betting-on-the-functional-beverage-boom", "source": "BriefGlance"},
            {"date": "2026-04-27", "headline": "Slice soda maker Suja Life files for IPO", "url": "https://www.fooddive.com/news/suja-life-slice-soda-ipo-files-public-offering/817329/", "source": "Food Dive"}
        ],
        "sources": [
            "https://briefglance.com/articles/suja-life-launches-ipo-betting-on-the-functional-beverage-boom",
            "https://www.fooddive.com/news/suja-life-slice-soda-ipo-files-public-offering/817329/",
            "https://www.kavout.com/market-lens/is-suja-life-s-ipo-a-refreshing-sip-or-a-bitter-pill-for-investors",
            "https://pitchbook.com/profiles/company/61111-63",
            "https://www.cbinsights.com/company/suja-life"
        ],
        "confidence": "medium",
        "confidence_note": "Revenue and market-share figures from credible third-party reporting; full S-1 not yet effective at research time, so management bios and equity-holder details are limited.",
    },
    # ========================================================== HAWK.US
    {
        "symbol": "HAWK.US",
        "name": "Blackhawk Network Holdings, Inc.",
        "researched_at": NOW,
        "one_liner": "Branded payments and gift-card platform connecting brands, retailers, and consumers — cards, prepaid, and corporate incentives.",
        "business_model": "Distributes physical and digital gift cards across 250k+ retail and digital points; takes a fee on every load. Also services corporate-incentive and rewards programmes.",
        "products_services": [
            "Physical gift cards distributed via grocery and convenience retail",
            "Digital gift card platform",
            "Prepaid telecom + financial products",
            "Corporate incentives + rewards programmes"
        ],
        "customers": "Retailers (Safeway, Kroger, Walmart, Target), consumer brands selling gift cards, and enterprises running employee/customer incentive programmes.",
        "revenue_geography": "US-led with international operations across UK, EU, ANZ.",
        "competitors": [
            {"name": "InComm Payments", "note": "primary US gift-card-distribution rival"},
            {"name": "Euronet Worldwide (epay)", "note": "global prepaid distribution competitor"},
            {"name": "Paysafe", "note": "prepaid and digital wallets overlap"}
        ],
        "moat": "Scale of retailer distribution network + exclusive long-tenure relationships with major grocers built over 25 years.",
        "market_position": "leader",
        "industry_trend": "neutral",
        "founded": 2001,
        "headquarters": "Pleasanton, California, USA",
        "key_people": [],
        "employees": None,
        "notable_investors": [
            "Silver Lake (private-equity owner since 2018 take-private)",
            "P2 Capital Partners (co-acquirer 2018)"
        ],
        "bull_points": [
            "Established branded-payments leader with multi-decade retailer relationships",
            "Digital gift-card mix shifting up improves unit economics",
            "Corporate-incentives segment offers diversification beyond consumer retail"
        ],
        "bear_points": [
            "Gift-card category structurally mature in the US; growth depends on digital mix and international",
            "Margin pressure from scale players (Walmart, Amazon) seeking lower fees",
            "Consumer payment innovation (BNPL, stablecoins, real-time payments) could erode prepaid relevance"
        ],
        "red_flags": [
            "EODHD lists this as a 2026-05-07 NYSE listing, but public sources indicate Blackhawk has been private since Silver Lake's $3.5B 2018 take-private. The 2026 listing event could not be independently confirmed in research — it may be a re-IPO/spin-off, a prospectus refile, or an EODHD calendar artefact."
        ],
        "catalysts": [
            "If genuine 2026 relisting: pricing and use-of-proceeds disclosures",
            "Digital gift-card volume growth metrics",
            "International segment scaling beyond US"
        ],
        "recent_news": [],
        "sources": [
            "https://en.wikipedia.org/wiki/Blackhawk_Network_Holdings",
            "https://www.pymnts.com/news/2013/blackhawk-completes-230-million-ipo/",
            "https://blackhawknetwork.com/company",
            "https://pitchbook.com/profiles/company/53628-94"
        ],
        "confidence": "low",
        "confidence_note": "EODHD calendar shows a 2026-05-07 NYSE listing under HAWK, but Blackhawk Network is documented as private since Silver Lake's 2018 take-private. Could not confirm a 2026 relisting in public sources during research — verify via prospectus before acting on this record.",
    },
    # ========================================================== BOT.US
    {
        "symbol": "BOT.US",
        "name": "Cbot Holdings Inc",
        "researched_at": NOW,
        "one_liner": "Historical CBOT Holdings ticker — operated the Chicago Board of Trade derivatives + options exchange. Merged with CME Group in 2007 (no longer independent).",
        "business_model": "Historically operated futures and options exchange via electronic and open-auction platforms; merged into CME Group 2007.",
        "products_services": [
            "Futures and options trading on agricultural, financial, and energy products (historical)"
        ],
        "customers": "Institutional traders, commercial hedgers, and broker-dealers (historical).",
        "revenue_geography": "US-led with global participation (historical).",
        "competitors": [
            {"name": "CME Group (parent post-2007)", "note": "merged entity"},
            {"name": "ICE Futures", "note": "primary historical competitor"}
        ],
        "moat": None,
        "market_position": "unclear",
        "industry_trend": "unclear",
        "founded": 1848,
        "headquarters": "Chicago, Illinois, USA",
        "key_people": [],
        "employees": None,
        "notable_investors": [
            "CME Group (acquired CBOT Holdings 2007)"
        ],
        "bull_points": [],
        "bear_points": [],
        "red_flags": [
            "EODHD shows a 2026-05-07 NASDAQ listing for BOT.US, but CBOT Holdings was acquired by CME Group in 2007 and is not an independent public company. The 2026 calendar entry could not be matched to any real listing event in research. Likely a stale ticker, ETF re-use, or different issuer mapped under an old code."
        ],
        "catalysts": [],
        "recent_news": [],
        "sources": [
            "https://en.wikipedia.org/wiki/Chicago_Board_of_Trade",
            "https://en.wikipedia.org/wiki/CME_Group",
            "https://www.cmegroup.com/company/cbot.html"
        ],
        "confidence": "low",
        "confidence_note": "Historical CBOT Holdings is part of CME Group since 2007. The 2026 EODHD calendar entry under BOT.US could not be reconciled with any current public-listing event. Treat the listing as unverified.",
    },
    # ========================================================== CLUB.US
    {
        "symbol": "CLUB.US",
        "name": "Town Sports International Holdings Inc",
        "researched_at": NOW,
        "one_liner": "Northeast / Mid-Atlantic US fitness-club operator (New York Sports Clubs, Boston Sports Clubs, Lucille Roberts) — historically public, currently OTC under CLUBQ after Nasdaq delisting.",
        "business_model": "Owns and operates approximately 185 fitness clubs across multiple regional brands, generating revenue from monthly memberships, personal-training fees, and ancillary services (group classes, kids programmes, summer camps).",
        "products_services": [
            "Gym memberships across New York Sports Clubs (99), Boston Sports Clubs (31), Lucille Roberts (16), Total Woman Gym & Spa (10), Washington / Philadelphia / Palm Beach Sports Clubs",
            "Personal and small-group training",
            "Children's fitness programmes and summer camps",
            "Pool, racquet, and basketball amenities at full-service clubs"
        ],
        "customers": "Urban Northeast / Mid-Atlantic US gym-going consumers.",
        "revenue_geography": "US (Northeast + Mid-Atlantic regional concentration).",
        "competitors": [
            {"name": "Planet Fitness", "note": "low-price scale leader stealing share"},
            {"name": "Equinox", "note": "premium-tier rival in NYC / urban markets"},
            {"name": "Life Time Fitness", "note": "premium full-service rival"},
            {"name": "Xponential Fitness brands", "note": "boutique-fitness disruption (Pure Barre, Club Pilates, etc.)"},
            {"name": "Crunch Fitness", "note": "mid-tier competitor"}
        ],
        "moat": "Real-estate footprint in dense Northeast urban markets; multi-brand approach segments price points.",
        "market_position": "challenger",
        "industry_trend": "headwind",
        "founded": 1973,
        "headquarters": "New York, New York, USA",
        "key_people": [],
        "employees": None,
        "notable_investors": [],
        "bull_points": [
            "Long-tenured Northeast brand recognition (NYSC, BSC)",
            "Diversified multi-brand portfolio across price points"
        ],
        "bear_points": [
            "Filed Chapter 11 bankruptcy in 2020; delisted from Nasdaq",
            "Currently trades OTC as CLUBQ — typically a sign of distress / restructuring",
            "Structural pressure from low-cost Planet Fitness + boutique-fitness disruption",
            "Northeast urban gym demand still recovering post-pandemic"
        ],
        "red_flags": [
            "Prior bankruptcy and Nasdaq delisting in 2020",
            "EODHD's 2026-05-07 NYSE listing entry conflicts with public sources showing the company on OTCMKTS as CLUBQ. No NYSE relisting found in research.",
            "Recurring negative cash flow and high debt-load history"
        ],
        "catalysts": [
            "If a genuine NYSE relisting did occur: prospectus terms and post-restructuring economics",
            "Membership growth re-acceleration in core NYC market",
            "Strategic transaction with private-equity sponsor"
        ],
        "recent_news": [],
        "sources": [
            "https://en.wikipedia.org/wiki/Town_Sports_International_Holdings",
            "https://www.americanspa.com/commercial-clubs/nasdaq-delists-town-sports-international",
            "https://www.bloomberg.com/profile/company/CLUB:US"
        ],
        "confidence": "low",
        "confidence_note": "Town Sports International filed Chapter 11 in 2020 and currently trades OTC as CLUBQ. EODHD's 2026-05-07 NYSE listing under CLUB could not be matched to any documented relisting event during research — verify via prospectus before acting.",
    },
    # ========================================================== RIKU.US
    {
        "symbol": "RIKU.US",
        "name": "Riku Dining Group Limited",
        "researched_at": NOW,
        "one_liner": "Operator and franchisor of Japanese-themed restaurants in Canada (Ajisen Ramen master franchise) and Hong Kong (Yakiniku Kakura, Yakiniku 801, Ufufu Café).",
        "business_model": "Mix of self-operated restaurants and sub-franchised locations. In Canada holds the exclusive master franchise for Ajisen Ramen — runs four self-operated stores and supports nine sub-franchisees. In Hong Kong franchises three Japanese restaurant brands.",
        "products_services": [
            "Ajisen Ramen (Canadian master franchise — 4 self-operated + 9 sub-franchised)",
            "Yakiniku Kakura — premium Hong Kong yakiniku",
            "Yakiniku 801 — value-focused Hong Kong yakiniku",
            "Ufufu Café — Japanese-Western café desserts and light meals (Hong Kong)"
        ],
        "customers": "Diners in Canada (ramen) and Hong Kong (yakiniku, café) — mass-market casual dining.",
        "revenue_geography": "Canada + Hong Kong only.",
        "competitors": [
            {"name": "Other Japanese-restaurant operators in Canada", "note": "Kinka Family / Guu / various ramen chains"},
            {"name": "Asian-themed casual chains in Hong Kong", "note": "Maxim's, Café de Coral, Cocoichi"},
            {"name": "Independent local Japanese restaurants", "note": "fragmented local competition"}
        ],
        "moat": "Master franchise rights for Ajisen Ramen in Canada provide a defensible territorial position; otherwise modest scale.",
        "market_position": "niche",
        "industry_trend": "neutral",
        "founded": 2025,
        "headquarters": "Hong Kong / Canada",
        "key_people": [],
        "employees": None,
        "notable_investors": [],
        "bull_points": [
            "Master-franchise rights provide territorial exclusivity for Ajisen Ramen in Canada",
            "Multi-brand exposure across two distinct geographies",
            "Asset-light sub-franchising model"
        ],
        "bear_points": [
            "Tiny scale — $16M revenue for 12 months ended Sept 2025",
            "Two-geography concentration with no presence in larger Asian or US markets",
            "Restaurant-industry margins thin and labour-cost pressured",
            "Small-cap restaurant IPOs face liquidity challenges post-listing"
        ],
        "red_flags": [
            "Filed to withdraw IPO registration on March 16, 2026 according to RenaissanceCapital reporting; subsequent refiling and listing on 2026-05-15 is the EODHD-listed expected date but the deal status was previously stalled."
        ],
        "catalysts": [
            "IPO completion (currently shown as 2026-05-15 expected on EODHD calendar)",
            "Ajisen Ramen Canadian unit-count growth",
            "Hong Kong same-store-sales recovery"
        ],
        "recent_news": [
            {"date": "2026-03-16", "headline": "Riku Dining Group filed to withdraw IPO registration; deal stalled", "url": "https://www.renaissancecapital.com/IPO-Center/News/117701/Japanese-style-restaurant-group-Riku-Dining-Group-sets-terms-for-$25-millio", "source": "Renaissance Capital"},
            {"date": "2026-05-15", "headline": "Riku Dining Group expected NASDAQ IPO at $4-$6/share, 5M shares (~$25M)", "url": "https://www.iposcoop.com/ipo/riku-dining-group/", "source": "IPOScoop"}
        ],
        "sources": [
            "https://www.iposcoop.com/ipo/riku-dining-group/",
            "https://www.renaissancecapital.com/IPO-Center/News/117701/Japanese-style-restaurant-group-Riku-Dining-Group-sets-terms-for-$25-millio",
            "https://stockanalysis.com/stocks/riku/company/",
            "https://www.tradingview.com/symbols/NASDAQ-RIKU/"
        ],
        "confidence": "medium",
        "confidence_note": "Small-cap restaurant IPO with limited English-language coverage. Withdrawal-then-relist sequence creates timing uncertainty — verify IPO actually prices on the expected date.",
    },
]


def main() -> None:
    written, failed = 0, 0
    for rec in RECORDS:
        proc = subprocess.run(
            [sys.executable, "-m", "backend.intel_write"],
            input=json.dumps(rec),
            text=True, capture_output=True, cwd=ROOT,
        )
        if proc.returncode == 0:
            written += 1
            print(proc.stdout.strip())
        else:
            failed += 1
            print(f"FAIL {rec['symbol']}: {proc.stderr.strip()}", file=sys.stderr)
    print(f"\nresearched: {written} written, {failed} failed")


if __name__ == "__main__":
    main()
