/* New Stocks — main frontend logic.
   Pure DOM construction (no innerHTML), uses NS.* helpers from sections.js. */

(function () {
  const NS = window.NS;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const STATUS_LABEL = { priced: "Priced", upcoming: "Upcoming", filed: "Filed" };
  const SLOW_PERIODS = new Set(["6m", "1y", "all"]);  // wider windows take longer to enrich

  let allStocks = [];
  let currentPeriod = "30d";
  let chart = null;
  let chartSeries = null;

  // Plan capabilities — populated from /api/capabilities at init.
  // Default optimistically; if the server says EOD is missing we hide
  // the chart pills, chart panel, and CSV buttons.
  NS.caps = { eod_history: true, live_quote: true, fundamentals: true,
              ipo_calendar: true, search: true, plan_hint: "" };

  async function loadCapabilities() {
    try {
      const r = await fetch("/api/capabilities");
      if (!r.ok) return;
      const c = await r.json();
      Object.assign(NS.caps, c);
    } catch { /* keep defaults */ }
  }

  // expose for search.js
  NS.openDossier = openDossier;

  // --------------------------------------------------- list

  function activePeriod() {
    const r = $('.filter-row[data-group="period"] input:checked');
    return r ? r.dataset.period : "30d";
  }

  async function loadList(force = false) {
    const list = $("#list");
    const period = activePeriod();
    currentPeriod = period;
    NS.clear(list);
    const slow = SLOW_PERIODS.has(period);
    list.append(NS.notice(slow
      ? `Fetching ${periodLabel(period)} window — wider periods take longer on first load (cached for 30 min)…`
      : "Fetching new listings…"));
    $("#refresh-btn").disabled = true;
    try {
      const base = force ? "/api/new-stocks/refresh" : "/api/new-stocks";
      const r = await fetch(`${base}?period=${encodeURIComponent(period)}`);
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        const err = new Error(body.message || `HTTP ${r.status}`);
        err.status = r.status;
        err.kind = body.error;
        throw err;
      }
      allStocks = await r.json();
      updatePillCounts();
      renderList();
    } catch (e) {
      NS.clear(list);
      if (e.status === 401 || e.kind === "eodhd_auth_error") {
        list.append(NS.notice(
          "EODHD API key not configured. Set EODHD_API_KEY in the server " +
          "environment and restart — the IPO calendar requires the " +
          "Fundamentals plan."));
      } else {
        list.append(NS.notice(`Could not load listings — ${e.message}.`));
      }
      updatePillCounts();
      updateListCounter(0);
    } finally {
      $("#refresh-btn").disabled = false;
    }
  }

  function periodLabel(p) {
    return ({ "7d": "7-day", "30d": "30-day", "90d": "90-day",
              "6m": "6-month", "1y": "1-year", "all": "10-year" })[p] || p;
  }

  function activeStatuses() {
    return $$('.filter-row[data-group="status"] input:checked').map(i => i.dataset.status);
  }
  function activeRegions() {
    return $$('.filter-row[data-group="region"] input:checked').map(i => i.dataset.region);
  }

  /* Per-pill absolute counts — number of items in the entire dataset that
     match THIS pill's value, regardless of whether it (or others) is
     checked. Lets the user see distribution at a glance. */
  function updatePillCounts() {
    const byStatus = new Map();
    const byRegion = new Map();
    for (const s of allStocks) {
      byStatus.set(s.status, (byStatus.get(s.status) || 0) + 1);
      const r = s.region || "OTHER";
      byRegion.set(r, (byRegion.get(r) || 0) + 1);
    }
    $$('.filter-row[data-group="status"] .filter-pill').forEach(pill => {
      const key = pill.querySelector("input").dataset.status;
      const n = byStatus.get(key) || 0;
      pill.querySelector("[data-pill-count]").textContent = String(n);
      pill.dataset.empty = n === 0 ? "1" : "0";
    });
    $$('.filter-row[data-group="region"] .filter-pill').forEach(pill => {
      const key = pill.querySelector("input").dataset.region;
      const n = byRegion.get(key) || 0;
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
    const items = allStocks.filter(s =>
      statusSet.has(s.status) && regionSet.has(s.region || "OTHER")
    );
    updateListCounter(items.length);
    if (items.length === 0) {
      list.append(NS.notice(allStocks.length === 0
        ? "No listings yet — refresh to fetch."
        : "No listings match the current filters."));
      return;
    }
    for (const s of items) list.append(buildRow(s));
  }

  /* ---------- row-figures ---------------------------------------
     Status-specific compact facts surfaced on each row, between
     description and tags. Editorial register: tracked-uppercase
     small label · monospace value, hairline-dot separators. */

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
    const ms = Date.now() - d.getTime();
    const days = Math.round(ms / 86_400_000);
    if (days === 0) return "today";
    if (days < 0) return null;             // future date — handled elsewhere
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
      if (typeof s.offer_price === "number" && typeof s.last_price === "number"
          && s.offer_price > 0) {
        const pct = (s.last_price - s.offer_price) / s.offer_price * 100;
        const sign = pct >= 0 ? "+" : "";
        const span = NS.el("span", { class: "fig-seg" },
          NS.el("span", { class: "fig-label", text: "ipo" }),
          NS.el("span", { class: "fig-value" },
            `${sym}${s.offer_price.toFixed(2)} → ${sym}${s.last_price.toFixed(2)} `,
            NS.el("span", {
              class: "fig-delta " + (pct >= 0 ? "pos" : "neg"),
              text: `${sign}${pct.toFixed(1)}%`,
            }),
          ),
        );
        segments.push(span);
      }
      const cap = fmtCompactMoney(s.market_cap, cur);
      if (cap) segments.push(figureSegment("cap", cap));
    } else if (s.status === "upcoming") {
      if (s.list_date) segments.push(figureSegment("expected", s.list_date));
      if (typeof s.price_low === "number" && typeof s.price_high === "number"
          && s.price_low > 0 && s.price_high > 0) {
        segments.push(figureSegment("range",
          `${sym}${s.price_low}–${sym}${s.price_high}`));
      } else if (typeof s.offer_price === "number" && s.offer_price > 0) {
        segments.push(figureSegment("offer", `${sym}${s.offer_price.toFixed(2)}`));
      }
      if (typeof s.shares === "number" && s.shares > 0) {
        const m = s.shares / 1e6;
        segments.push(figureSegment("shares", `${m.toFixed(1)}M`));
        if (typeof s.price_high === "number" && typeof s.price_low === "number"
            && s.price_low > 0) {
          const mid = (s.price_low + s.price_high) / 2;
          segments.push(figureSegment("est. raise", fmtCompactMoney(s.shares * mid, cur)));
        }
      }
    } else if (s.status === "filed") {
      if (s.filing_date) segments.push(figureSegment("filed", s.filing_date));
      if (typeof s.price_low === "number" && typeof s.price_high === "number"
          && s.price_low > 0 && s.price_high > 0) {
        segments.push(figureSegment("range",
          `${sym}${s.price_low}–${sym}${s.price_high}`));
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

  function buildRow(s) {
    const logo = s.logo_url
      ? NS.el("img", { class: "row-logo", src: s.logo_url, alt: "", loading: "lazy" })
      : NS.el("span", { class: "row-logo--blank" });

    // CSV button only when EOD history is on the active plan.
    const csv = NS.caps.eod_history
      ? NS.el("a", {
          class: "row-csv",
          href: `/api/stock/${encodeURIComponent(s.symbol)}/download.csv`,
          download: true,
          onclick: (e) => e.stopPropagation(),
        }, "↓ CSV")
      : null;

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
        openDossier(s.symbol, s);
      },
    },
      logo,
      name,
      price,
      csv,
      s.description ? NS.el("div", { class: "row-desc", text: s.description }) : null,
      figures,
      tagsNode,
    );
  }

  // --------------------------------------------------- dossier

  async function openDossier(symbol, baseFromList) {
    const overlay = $("#dossier");
    const body = $("#dossier-body");
    NS.clear(body);
    body.append(NS.notice(`Loading ${symbol}…`));
    overlay.hidden = false;
    document.body.style.overflow = "hidden";

    try {
      const r = await fetch(`/api/stock/${encodeURIComponent(symbol)}/full`);
      if (!r.ok) {
        const t = await r.json().catch(() => ({}));
        throw new Error(t.message || `HTTP ${r.status}`);
      }
      const detail = await r.json();
      renderDossier(detail);
      initChart(symbol, "1y");
    } catch (e) {
      NS.clear(body);
      body.append(NS.notice(`Could not load detail — ${e.message}.`));
    }
  }

  function renderDossier(d) {
    const body = $("#dossier-body");
    NS.clear(body);
    const base = d.base || {};

    // ---- frontispiece
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

    // ---- stat block
    const statBlock = NS.renderStatBlock(d.stats);
    if (statBlock) body.append(statBlock);

    // ---- chart (only when EOD history is on the active plan)
    if (NS.caps.eod_history) {
      const ranges = [["1d","1D"],["1w","1W"],["1mo","1M"],["6mo","6M"],["1y","1Y"],["5y","5Y"],["max","Max"]];
      const rangeRow = NS.el("div", { class: "range-row", role: "tablist" });
      ranges.forEach(([k, lbl]) => {
        rangeRow.append(NS.el("button", {
          class: "range-pill" + (k === "1y" ? " active" : ""),
          dataset: { range: k },
          onclick: (e) => {
            $$(".range-pill", body).forEach(b => b.classList.remove("active"));
            e.currentTarget.classList.add("active");
            initChart(base.symbol, k);
          },
        }, lbl));
      });
      body.append(rangeRow);
      body.append(NS.el("div", { id: "chart" }));
    } else {
      body.append(NS.el("div", { class: "section" },
        NS.notice(
          "Historical chart unavailable on current EODHD plan. " +
          "Add 'EOD All World' (€19.99) — restart the server after upgrade."
        )));
    }

    // ---- substantive sections
    const fin = NS.renderFinancials(d.financials);     if (fin) body.append(fin);
    const an  = NS.renderAnalyst(d.analyst, base.currency); if (an)  body.append(an);
    const ho  = NS.renderHolders(d.top_holders);        if (ho)  body.append(ho);
    const ins = NS.renderInsider(d.insider_recent, base.currency); if (ins) body.append(ins);
    const ea  = NS.renderEarnings(d.earnings_history, d.next_earnings, base.currency); if (ea) body.append(ea);
    const sd  = NS.renderSplitsDivs(d.splits_divs, base.currency); if (sd) body.append(sd);

    // ---- intelligence (lazy-loaded; only renders if a record exists)
    const intelAnchor = NS.el("div", { class: "intel-anchor" });
    body.append(intelAnchor);
    fetchAndRenderIntelligence(base.symbol, intelAnchor);

    // ---- actions
    const actions = NS.el("div", { class: "dossier-actions" });
    if (NS.caps.eod_history) {
      actions.append(NS.el("a", {
        class: "btn-solid",
        href: `/api/stock/${encodeURIComponent(base.symbol)}/download.csv`,
        download: true,
      }, "↓ Download CSV"));
    }
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
    body.append(actions);

    // ---- tags
    if ((base.tags || []).length > 0) {
      const t = NS.el("div", { class: "dossier-tags" });
      base.tags.forEach((tag, i) => {
        if (i > 0) t.append(NS.el("span", { class: "sep", text: "·" }));
        t.append(NS.el("span", { text: tag }));
      });
      body.append(t);
    }
  }

  async function fetchAndRenderIntelligence(symbol, anchor) {
    try {
      const r = await fetch(`/api/stock/${encodeURIComponent(symbol)}/intelligence`);
      if (r.status === 404) {
        anchor.append(NS.el("div", { class: "intel-empty" },
          NS.el("p", { class: "intel-empty-line",
            text: "No intelligence record yet — runs nightly via /research-stocks." })));
        return;
      }
      if (!r.ok) return;
      const intel = await r.json();
      const sec = NS.renderIntelligence(intel);
      if (sec) anchor.append(sec);
    } catch { /* silent — intelligence is optional */ }
  }

  function closeDossier() {
    $("#dossier").hidden = true;
    document.body.style.overflow = "";
    if (chart) { chart.remove(); chart = null; chartSeries = null; }
  }

  // --------------------------------------------------- chart

  async function initChart(symbol, range) {
    const elNode = $("#chart");
    if (!elNode) return;
    NS.clear(elNode);
    if (chart) { chart.remove(); chart = null; }
    if (!window.LightweightCharts) {
      elNode.append(NS.notice("Chart library failed to load."));
      return;
    }
    chart = LightweightCharts.createChart(elNode, {
      layout: { background: { color: "#fff" }, textColor: "#000",
                fontFamily: "JetBrains Mono, monospace", fontSize: 11 },
      grid: { vertLines: { color: "#eee" }, horzLines: { color: "#eee" } },
      rightPriceScale: { borderColor: "#000" },
      timeScale: { borderColor: "#000", timeVisible: range === "1d" || range === "1w", secondsVisible: false },
      crosshair: { mode: 1 },
    });
    chartSeries = chart.addLineSeries({
      color: "#000", lineWidth: 1.5,
      priceLineVisible: false, lastValueVisible: true,
    });
    try {
      const r = await fetch(`/api/stock/${encodeURIComponent(symbol)}/history?range=${range}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const rows = await r.json();
      if (!rows.length) {
        NS.clear(elNode);
        elNode.append(NS.notice("No price history available yet."));
        return;
      }
      const data = rows.map(row => {
        const t = row.t.length > 10 ? Math.floor(new Date(row.t).getTime() / 1000) : row.t.slice(0, 10);
        return { time: t, value: row.c };
      });
      chartSeries.setData(data);
      chart.timeScale().fitContent();
    } catch (e) {
      NS.clear(elNode);
      elNode.append(NS.notice(`Chart unavailable — ${e.message}.`));
    }
  }

  // --------------------------------------------------- wire-up

  async function init() {
    await loadCapabilities();
    loadList(false);
    $("#refresh-btn").addEventListener("click", () => loadList(true));

    // Period radios re-fetch (different EODHD window, different cache key).
    $$('.filter-row[data-group="period"] input').forEach(inp =>
      inp.addEventListener("change", () => loadList(false)));

    // Status / region filters narrow the already-loaded set in-memory.
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
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
