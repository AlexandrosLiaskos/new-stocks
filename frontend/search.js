/* Discreet ticker search. Uses /api/search; opens dossier on click. */

(function () {
  const NS = window.NS;
  const $ = (s, r = document) => r.querySelector(s);

  let lastQuery = "";
  let timer = null;

  function init() {
    const input = $("#search-input");
    const panel = $("#search-results");
    if (!input || !panel) return;

    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { panel.hidden = true; return; }
      timer = setTimeout(() => runSearch(q, panel), 220);
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

  async function runSearch(q, panel) {
    if (q === lastQuery) { panel.hidden = false; return; }
    lastQuery = q;
    NS.clear(panel);
    panel.append(NS.el("div", { class: "search-result" },
      NS.el("span", { class: "sr-name", text: "searching…" })));
    panel.hidden = false;

    try {
      const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const hits = await r.json();
      NS.clear(panel);
      if (!hits.length) {
        panel.append(NS.el("div", { class: "search-result" },
          NS.el("span", { class: "sr-name", text: "no matches" })));
        return;
      }
      for (const h of hits.slice(0, 10)) {
        const meta = [h.country, h.exchange, h.type, h.currency].filter(Boolean).join(" · ");
        const row = NS.el("div", {
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
        );
        panel.append(row);
      }
    } catch (e) {
      NS.clear(panel);
      panel.append(NS.el("div", { class: "search-result" },
        NS.el("span", { class: "sr-name", text: `error · ${e.message}` })));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
