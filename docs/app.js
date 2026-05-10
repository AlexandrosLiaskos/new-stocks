/* New Stocks — STATIC build of the frontend.

   Reads pre-baked JSON from data/* — no /api/, no live EODHD calls.
   Period / status / region filters all run client-side on listings.json. */

(function () {
  const NS = window.NS;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const STATUS_LABEL = { priced: "Priced", upcoming: "Upcoming", filed: "Filed" };

  // Period → days of lookback. Lookahead always includes "future" status rows.
  const PERIOD_DAYS = { "7d": 7, "30d": 30, "90d": 90, "6m": 180, "1y": 365, "all": 3650 };

  let allStocks = [];
  let currentPeriod = "30d";

  // Capabilities baked at build time. Static site never has live EOD,
  // so chart pills + CSV button are never rendered.
  NS.caps = {
    eod_history: false, live_quote_baked_in: true,
    fundamentals: true, ipo_calendar: true, intelligence: true,
  };
  NS.openDossier = openDossier;

  // ---------------------------------------------------- bootstrap

  async function init() {
    await loadManifest();
    await loadList();

    $$('.filter-row[data-group="period"] input').forEach(inp =>
      inp.addEventListener("change", () => {
        currentPeriod = activePeriod();
        renderList();
      }));
    $$('.filter-row[data-group="status"] input, .filter-row[data-group="region"] input')
      .forEach(inp => inp.addEventListener("change", renderList));

    $(".dossier-close").addEventListener("click", closeDossier);
    $("#dossier").addEventListener("click", (e) => {
      if (e.target.id === "dossier") closeDossier();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !$("#dossier").hidden) closeDossier();
    });
  }

  async function loadManifest() {
    try {
      const r = await fetch("data/manifest.json", { cache: "no-store" });
      if (!r.ok) return;
      const m = await r.json();
      const built = (m.built_at || "").slice(0, 16).replace("T", " ");
      const node = $("#built-at");
      if (node) {
        node.textContent = `built ${built} UTC · ${m.counts?.listings ?? "?"} listings · ${m.counts?.intelligence ?? "?"} researched`;
      }
    } catch { /* manifest is informational */ }
  }

  // ---------------------------------------------------- list

  async function loadList() {
    const list = $("#list");
    NS.clear(list);
    list.append(NS.notice("Loading listings…"));
    try {
      const r = await fetch("data/listings.json", { cache: "default" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      allStocks = await r.json();
      currentPeriod = activePeriod();
      updatePillCounts();
      renderList();
    } catch (e) {
      NS.clear(list);
      list.append(NS.notice(
        `Could not load listings — ${e.message}. The static site needs ` +
        `data/listings.json — re-run \`python -m backend.build_static\`.`));
      updateListCounter(0);
    }
  }

  function activePeriod() {
    const r = $('.filter-row[data-group="period"] input:checked');
    return r ? r.dataset.period : "30d";
  }

  function activeStatuses() {
    return $$('.filter-row[data-group="status"] input:checked').map(i => i.dataset.status);
  }

  function activeRegions() {
    return $$('.filter-row[data-group="region"] input:checked').map(i => i.dataset.region);
  }

  /* Period filter is now pure date math on the loaded listings. */
  function withinPeriod(s, period) {
    const days = PERIOD_DAYS[period];
    if (!days) return true;
    const today = new Date();
    const cutoff = new Date(today.getTime() - days * 86_400_000);
    const ref = s.list_date || s.filing_date || s.amended_date;
    if (!ref) return true;            // unknown dates always shown
    const d = new Date(ref + "T00:00:00Z");
    if (isNaN(d.getTime())) return true;
    if (d > today) return true;        // future-dated (upcoming) always shown
    return d >= cutoff;
  }

  function updatePillCounts() {
    const byStatus = new Map();
    const byRegion = new Map();
    const byPeriod = new Map();
    for (const s of allStocks) {
      byStatus.set(s.status, (byStatus.get(s.status) || 0) + 1);
      const r = s.region || "OTHER";
      byRegion.set(r, (byRegion.get(r) || 0) + 1);
      for (const p of Object.keys(PERIOD_DAYS)) {
        if (withinPeriod(s, p)) byPeriod.set(p, (byPeriod.get(p) || 0) + 1);
      }
    }
    setCounts('.filter-row[data-group="status"] .filter-pill', "status", byStatus);
    setCounts('.filter-row[data-group="region"] .filter-pill', "region", byRegion);
    setCounts('.filter-row[data-group="period"] .filter-pill', "period", byPeriod);
  }

  function setCounts(selector, key, map) {
    $$(selector).forEach(pill => {
      const k = pill.querySelector("input").dataset[key];
      const n = map.get(k) || 0;
      pill.querySelector("[data-pill-count]").textContent = String(n);
      pill.dataset.empty = n === 0 ? "1" : "0";
    });
  }

  function updateListCounter(visible) {
    const node = $("#list-counter");
    if (!node) return;
    NS.clear(node);
    if (allStocks.length === 0) { node.textContent = ""; return; }
    node.append(
      NS.el("span", { class: "lc-shown", text: String(visible) }),
      NS.el("span", { class: "lc-sep", text: "/" }),
      NS.el("span", { class: "lc-total", text: String(allStocks.length) }),
    );
  }

  function renderList() {
    const list = $("#list");
    NS.clear(list);
    const statusSet = new Set(activeStatuses());
    const regionSet = new Set(activeRegions());
    const period = activePeriod();
    const items = allStocks.filter(s =>
      statusSet.has(s.status) &&
      regionSet.has(s.region || "OTHER") &&
      withinPeriod(s, period)
    );
    updateListCounter(items.length);
    if (items.length === 0) {
      list.append(NS.notice(allStocks.length === 0
        ? "No listings yet."
        : "No listings match the current filters."));
      return;
    }
    for (const s of items) list.append(buildRow(s));
  }

  function buildRow(s) {
    const logo = s.logo_url
      ? NS.el("img", { class: "row-logo", src: s.logo_url, alt: "", loading: "lazy" })
      : NS.el("span", { class: "row-logo--blank" });

    const name = NS.el("div", { class: "row-name" },
      s.name,
      NS.el("span", { class: "row-symbol", text: s.symbol }),
    );

    const priceTxt = NS.fmtPrice(s.last_price ?? s.offer_price, s.currency)
      || (s.price_low && s.price_high ? `${NS.cursym(s.currency)}${s.price_low}–${s.price_high}` : "—");
    const priceHasValue = priceTxt !== "—";
    const price = NS.el("div", { class: priceHasValue ? "row-price" : "row-price muted", text: priceTxt });
    if (typeof s.change_pct === "number") {
      const pct = s.change_pct;
      price.append(NS.el("span", {
        class: "row-change " + (pct >= 0 ? "pos" : "neg"),
        text: NS.fmtChangePct(pct),
      }));
    }

    const tagsNode = NS.el("div", { class: "row-tags" });
    (s.tags || []).slice(0, 6).forEach((t, i) => {
      if (i > 0) tagsNode.append(NS.el("span", { class: "sep", text: "·" }));
      const isStatus = (t || "").toLowerCase() === s.status;
      tagsNode.append(NS.el("span", { class: isStatus ? "tag-status" : null, text: t }));
    });

    const figures = buildFiguresLine(s);

    return NS.el("article", {
      class: "row",
      dataset: { symbol: s.symbol },
      onclick: (e) => {
        if (e.target.closest(".row-csv")) return;
        openDossier(s.symbol);
      },
    },
      logo,
      name,
      price,
      s.description ? NS.el("div", { class: "row-desc", text: s.description }) : null,
      figures,
      tagsNode,
    );
  }

  // ---------------------------------------------------- figures (status-specific facts)

  function fmtCompactMoney(v, currency) {
    if (typeof v !== "number" || !isFinite(v) || v === 0) return null;
    const sym = NS.cursym(currency);
    const a = Math.abs(v);
    if (a >= 1e12) return `${sym}${(v / 1e12).toFixed(2)}T`;
    if (a >= 1e9)  return `${sym}${(v / 1e9 ).toFixed(2)}B`;
    if (a >= 1e6)  return `${sym}${(v / 1e6 ).toFixed(2)}M`;
    if (a >= 1e3)  return `${sym}${(v / 1e3 ).toFixed(2)}K`;
    return `${sym}${v.toFixed(2)}`;
  }

  function daysAgo(iso) {
    if (!iso) return null;
    const d = new Date(iso + "T00:00:00Z");
    if (isNaN(d.getTime())) return null;
    const days = Math.round((Date.now() - d.getTime()) / 86_400_000);
    if (days === 0) return "today";
    if (days < 0) return null;
    if (days < 30) return `${days}d ago`;
    if (days < 365) return `${Math.round(days / 30)}mo ago`;
    return `${Math.round(days / 365)}y ago`;
  }

  function figureSegment(label, value) {
    if (!value) return null;
    return NS.el("span", { class: "fig-seg" },
      NS.el("span", { class: "fig-label", text: label }),
      NS.el("span", { class: "fig-value", text: value }),
    );
  }

  function buildFiguresLine(s) {
    const segments = [];
    const cur = s.currency;
    const sym = NS.cursym(cur);
    if (s.status === "priced") {
      const since = daysAgo(s.list_date);
      if (since) segments.push(figureSegment("listed", since));
      if (typeof s.offer_price === "number" && typeof s.last_price === "number" && s.offer_price > 0) {
        const pct = (s.last_price - s.offer_price) / s.offer_price * 100;
        const sign = pct >= 0 ? "+" : "";
        segments.push(NS.el("span", { class: "fig-seg" },
          NS.el("span", { class: "fig-label", text: "ipo" }),
          NS.el("span", { class: "fig-value" },
            `${sym}${s.offer_price.toFixed(2)} → ${sym}${s.last_price.toFixed(2)} `,
            NS.el("span", { class: "fig-delta " + (pct >= 0 ? "pos" : "neg"), text: `${sign}${pct.toFixed(1)}%` }),
          ),
        ));
      }
      const cap = fmtCompactMoney(s.market_cap, cur);
      if (cap) segments.push(figureSegment("cap", cap));
    } else if (s.status === "upcoming") {
      if (s.list_date) segments.push(figureSegment("expected", s.list_date));
      if (typeof s.price_low === "number" && typeof s.price_high === "number" && s.price_low > 0) {
        segments.push(figureSegment("range", `${sym}${s.price_low}–${sym}${s.price_high}`));
      } else if (typeof s.offer_price === "number" && s.offer_price > 0) {
        segments.push(figureSegment("offer", `${sym}${s.offer_price.toFixed(2)}`));
      }
      if (typeof s.shares === "number" && s.shares > 0) {
        segments.push(figureSegment("shares", `${(s.shares / 1e6).toFixed(1)}M`));
        if (typeof s.price_high === "number" && typeof s.price_low === "number" && s.price_low > 0) {
          const mid = (s.price_low + s.price_high) / 2;
          segments.push(figureSegment("est. raise", fmtCompactMoney(s.shares * mid, cur)));
        }
      }
    } else if (s.status === "filed") {
      if (s.filing_date) segments.push(figureSegment("filed", s.filing_date));
      if (typeof s.price_low === "number" && typeof s.price_high === "number" && s.price_low > 0) {
        segments.push(figureSegment("range", `${sym}${s.price_low}–${sym}${s.price_high}`));
      }
    }
    if (segments.length === 0) return null;
    const line = NS.el("div", { class: "row-figures" });
    segments.forEach((seg, i) => {
      if (i > 0) line.append(NS.el("span", { class: "sep", text: "·" }));
      line.append(seg);
    });
    return line;
  }

  // ---------------------------------------------------- dossier

  async function openDossier(symbol) {
    const overlay = $("#dossier");
    const body = $("#dossier-body");
    NS.clear(body);
    body.append(NS.notice(`Loading ${symbol}…`));
    overlay.hidden = false;
    document.body.style.overflow = "hidden";

    try {
      const path = `data/full/${encodeURIComponent(symbol)}.json`;
      const r = await fetch(path, { cache: "default" });
      if (!r.ok) {
        // No baked dossier — degrade to whatever we can show from the listing row.
        const row = allStocks.find(s => s.symbol === symbol);
        if (row) {
          renderDossier({ base: row, stats: [], financials: { rows: [] }, analyst: {},
                          top_holders: [], insider_recent: [], earnings_history: [],
                          next_earnings: null, splits_divs: { splits: [], dividends: [] } });
          fetchAndRenderNews(symbol, dossierNewsAnchor());
          fetchAndRenderIntelligence(symbol, dossierIntelAnchor());
          return;
        }
        throw new Error(`HTTP ${r.status}`);
      }
      const detail = await r.json();
      renderDossier(detail);
      fetchAndRenderNews(symbol, dossierNewsAnchor());
      fetchAndRenderIntelligence(symbol, dossierIntelAnchor());
    } catch (e) {
      NS.clear(body);
      body.append(NS.notice(`Could not load detail — ${e.message}.`));
    }
  }

  function dossierIntelAnchor() { return $("#dossier-body .intel-anchor"); }
  function dossierNewsAnchor() { return $("#dossier-body .news-anchor"); }

  function renderDossier(d) {
    const body = $("#dossier-body");
    NS.clear(body);
    const base = d.base || {};

    const eyebrow = [STATUS_LABEL[base.status] || base.status, base.exchange, base.list_date]
      .filter(Boolean).join(" · ") || "New listing";
    body.append(NS.el("div", { class: "dossier-eyebrow", text: eyebrow }));

    const title = NS.el("h2", { class: "dossier-title", id: "dossier-title" });
    const parts = (base.name || base.symbol).split(" ");
    if (parts.length >= 2) {
      title.append(parts.slice(0, -1).join(" ") + " ");
      title.append(NS.el("em", { text: parts[parts.length - 1] }));
    } else {
      title.append(NS.el("em", { text: parts[0] }));
    }
    body.append(title);
    body.append(NS.el("hr", { class: "dossier-rule" }));
    if (base.description) body.append(NS.el("p", { class: "dossier-lede", text: base.description }));

    const statBlock = NS.renderStatBlock(d.stats);
    if (statBlock) body.append(statBlock);

    // Chart is intentionally omitted on the static build (no EOD on plan).

    const fin = NS.renderFinancials(d.financials);     if (fin) body.append(fin);
    const an  = NS.renderAnalyst(d.analyst, base.currency); if (an)  body.append(an);
    const ho  = NS.renderHolders(d.top_holders);        if (ho)  body.append(ho);
    const ins = NS.renderInsider(d.insider_recent, base.currency); if (ins) body.append(ins);
    const ea  = NS.renderEarnings(d.earnings_history, d.next_earnings, base.currency); if (ea) body.append(ea);
    const sd  = NS.renderSplitsDivs(d.splits_divs, base.currency); if (sd) body.append(sd);

    body.append(NS.el("div", { class: "news-anchor" }));    // EODHD news renders here
    body.append(NS.el("div", { class: "intel-anchor" }));   // Claude-researched intelligence renders here

    const actions = NS.el("div", { class: "dossier-actions" });
    if (base.prospectus_url) {
      actions.append(NS.el("a", {
        class: "btn-solid", href: base.prospectus_url, target: "_blank", rel: "noopener",
      }, "Prospectus → SEC"));
    }
    if (base.web_url) {
      actions.append(NS.el("a", {
        class: "btn-solid", href: base.web_url, target: "_blank", rel: "noopener",
      }, "Company website ↗"));
    }
    if (actions.children.length > 0) body.append(actions);

    if ((base.tags || []).length > 0) {
      const t = NS.el("div", { class: "dossier-tags" });
      base.tags.forEach((tag, i) => {
        if (i > 0) t.append(NS.el("span", { class: "sep", text: "·" }));
        t.append(NS.el("span", { text: tag }));
      });
      body.append(t);
    }
  }

  async function fetchAndRenderNews(symbol, anchor) {
    if (!anchor) return;
    try {
      const r = await fetch(`data/news/${encodeURIComponent(symbol)}.json`, { cache: "default" });
      if (!r.ok) return;            // silent — no news file means no news
      const items = await r.json();
      const sec = NS.renderNews(items);
      if (sec) anchor.append(sec);
    } catch { /* silent */ }
  }

  async function fetchAndRenderIntelligence(symbol, anchor) {
    if (!anchor) return;
    try {
      const r = await fetch(`data/intelligence/${encodeURIComponent(symbol)}.json`, { cache: "default" });
      if (r.status === 404 || !r.ok) {
        anchor.append(NS.el("div", { class: "intel-empty" },
          NS.el("p", { class: "intel-empty-line",
            text: "No intelligence record yet — populated daily by /research-stocks." })));
        return;
      }
      const intel = await r.json();
      const sec = NS.renderIntelligence(intel);
      if (sec) anchor.append(sec);
    } catch { /* silent — intelligence is optional */ }
  }

  function closeDossier() {
    $("#dossier").hidden = true;
    document.body.style.overflow = "";
  }

  // ----------------------------------------------------

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
