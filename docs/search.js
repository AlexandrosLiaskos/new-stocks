/* Discreet ticker search — STATIC build.

   Loads data/search.json once on first interaction, then filters
   client-side. Hits in the index map to either:
     - a baked dossier under data/full/{symbol}.json (priced/upcoming/filed)
     - or a research-only entry (intelligence record exists but no listing)
   Either way, clicking opens the dossier exactly like a list-row click. */

(function () {
  const NS = window.NS;
  const $ = (s, r = document) => r.querySelector(s);

  let index = null;
  let timer = null;
  let lastQuery = "";

  function init() {
    const input = $("#search-input");
    const panel = $("#search-results");
    if (!input || !panel) return;

    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 1) { panel.hidden = true; return; }
      timer = setTimeout(() => runSearch(q, panel), 80);
    });
    input.addEventListener("focus", () => {
      if (lastQuery && panel.children.length > 0) panel.hidden = false;
    });
    document.addEventListener("click", (e) => {
      if (!panel.contains(e.target) && e.target !== input) panel.hidden = true;
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden) panel.hidden = true;
    });
  }

  async function ensureIndex() {
    if (index) return index;
    try {
      const r = await fetch("data/search.json", { cache: "default" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      index = await r.json();
    } catch {
      index = [];
    }
    return index;
  }

  async function runSearch(q, panel) {
    if (q === lastQuery) { panel.hidden = false; return; }
    lastQuery = q;
    NS.clear(panel);
    panel.append(NS.el("div", { class: "search-result" },
      NS.el("span", { class: "sr-name", text: "searching…" })));
    panel.hidden = false;

    const idx = await ensureIndex();
    const needle = q.toLowerCase();
    const hits = [];
    for (const item of idx) {
      const sym = (item.symbol || "").toLowerCase();
      const name = (item.name || "").toLowerCase();
      let score = 0;
      if (sym === needle) score = 100;
      else if (sym.startsWith(needle)) score = 80;
      else if (sym.includes(needle)) score = 50;
      if (name.startsWith(needle)) score = Math.max(score, 60);
      else if (name.includes(needle)) score = Math.max(score, 30);
      if (score > 0) hits.push({ ...item, _score: score });
    }
    hits.sort((a, b) => b._score - a._score);

    NS.clear(panel);
    if (!hits.length) {
      panel.append(NS.el("div", { class: "search-result" },
        NS.el("span", { class: "sr-name", text: "no matches" })));
      return;
    }
    for (const h of hits.slice(0, 10)) {
      const meta = [h.country, h.exchange, h.type, h.currency].filter(Boolean).join(" · ");
      panel.append(NS.el("div", {
        class: "search-result",
        onclick: () => {
          panel.hidden = true;
          $("#search-input").value = "";
          window.NS.openDossier(h.symbol);
        },
      },
        NS.el("span", { class: "sr-name", text: h.name }),
        NS.el("span", { class: "sr-sym", text: h.symbol }),
        NS.el("span", { class: "sr-meta", text: meta }),
      ));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
