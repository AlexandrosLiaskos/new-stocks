/* Dossier section renderers — pure DOM (createElement / textContent).
   Every public function takes a payload slice and returns an element to
   append. No innerHTML, no template strings of HTML. */

const NS = (window.NS = window.NS || {});

NS.el = function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
};
NS.clear = function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
};
NS.notice = function notice(msg) {
  return NS.el("div", { class: "notice", text: msg });
};

/* Currency-aware price formatter (mirrors backend.format_utils.fmt_money) */
NS.CURRENCY_SYMBOLS = {
  USD: "$", EUR: "€", GBP: "£", GBX: "p", JPY: "¥", CNY: "¥", HKD: "HK$",
  TWD: "NT$", INR: "₹", AUD: "A$", NZD: "NZ$", CAD: "C$", CHF: "CHF",
  SEK: "kr", NOK: "kr", DKK: "kr", SGD: "S$", KRW: "₩", BRL: "R$",
  MXN: "Mex$", ZAR: "R", RUB: "₽", TRY: "₺", ILS: "₪", PLN: "zł",
  CZK: "Kč", HUF: "Ft", THB: "฿", IDR: "Rp", MYR: "RM", PHP: "₱", VND: "₫",
};
NS.cursym = function cursym(c) { return NS.CURRENCY_SYMBOLS[(c || "").toUpperCase()] || (c || ""); };

NS.fmtPrice = function fmtPrice(price, currency) {
  if (typeof price !== "number" || !isFinite(price) || price <= 0) return "—";
  return `${NS.cursym(currency)}${price.toFixed(2)}`;
};
NS.fmtChangePct = function fmtChangePct(p) {
  if (typeof p !== "number" || !isFinite(p)) return "";
  const sign = p > 0 ? "+" : "";
  return `${sign}${p.toFixed(2)}%`;
};
NS.fmtSigned = function fmtSigned(p, decimals = 2) {
  if (typeof p !== "number" || !isFinite(p)) return "—";
  const sign = p > 0 ? "+" : "";
  return `${sign}${p.toFixed(decimals)}`;
};

/* ----------------------------------------------------------------- section header */
NS.sectionHead = function sectionHead(title, subtitle) {
  const head = NS.el("div", { class: "section-head" },
    NS.el("h3", { class: "section-title", text: title }),
  );
  const wrap = NS.el("section", { class: "section" }, head);
  if (subtitle) wrap.append(NS.el("p", { class: "section-sub", text: subtitle }));
  return wrap;
};

/* ----------------------------------------------------------------- stat block */
NS.renderStatBlock = function renderStatBlock(stats) {
  if (!stats || stats.length === 0) return null;
  const mid = Math.ceil(stats.length / 2);
  const colA = stats.slice(0, mid);
  const colB = stats.slice(mid);
  const buildCol = (col) => {
    const c = NS.el("div", { class: "stat-col" });
    for (const s of col) {
      c.append(NS.el("div", { class: "stat" },
        NS.el("div", { class: "stat-label", text: s.label }),
        NS.el("div", { class: "stat-value", text: s.value }),
      ));
    }
    return c;
  };
  return NS.el("div", { class: "stat-block" },
    buildCol(colA),
    NS.el("div", { class: "stat-divider" }),
    buildCol(colB),
  );
};

/* ----------------------------------------------------------------- financials */
NS.renderFinancials = function renderFinancials(fin) {
  if (!fin || !fin.rows || fin.rows.length === 0) return null;
  const sec = NS.sectionHead("Financials", fin.fiscal_year_end ? `Fiscal year ends ${fin.fiscal_year_end}` : null);
  const periods = fin.rows[0].period_labels;

  const table = NS.el("table", { class: "fin-table" });
  const thead = NS.el("thead");
  const trh = NS.el("tr");
  trh.append(NS.el("th", { class: "fin-label", text: "" }));
  for (const p of periods) trh.append(NS.el("th", { text: p }));
  thead.append(trh);
  table.append(thead);

  const tbody = NS.el("tbody");
  for (const row of fin.rows) {
    const tr = NS.el("tr");
    tr.append(NS.el("td", { class: "fin-label", text: row.label }));
    for (const v of row.values) tr.append(NS.el("td", { text: v }));
    tbody.append(tr);
  }
  table.append(tbody);
  sec.append(table);

  if (fin.reporting_currency) {
    sec.append(NS.el("p", { class: "fin-foot", text: `reporting currency · ${fin.reporting_currency}` }));
  }
  return sec;
};

/* ----------------------------------------------------------------- analyst */
NS.renderAnalyst = function renderAnalyst(a, baseCurrency) {
  if (!a) return null;
  const total = (a.strong_buy || 0) + (a.buy || 0) + (a.hold || 0) + (a.sell || 0) + (a.strong_sell || 0);
  if (total === 0 && a.rating == null && a.target_price == null) return null;

  const sec = NS.sectionHead("Analyst Consensus");
  const grid = NS.el("div", { class: "analyst-grid" });

  const ratingText = (typeof a.rating === "number")
    ? a.rating.toFixed(2)
    : "—";
  grid.append(NS.el("div", { class: "analyst-cell" },
    NS.el("div", { class: "analyst-label", text: "Rating" }),
    NS.el("div", { class: "analyst-value" },
      ratingText,
      NS.el("span", { class: "analyst-value-suffix", text: "/ 5" }),
    ),
  ));

  const tgt = (typeof a.target_price === "number")
    ? `${NS.cursym(baseCurrency)}${a.target_price.toFixed(2)}`
    : "—";
  const pct = (typeof a.target_pct_vs_current === "number")
    ? `${a.target_pct_vs_current >= 0 ? "+" : ""}${a.target_pct_vs_current.toFixed(1)}%`
    : "";
  grid.append(NS.el("div", { class: "analyst-cell" },
    NS.el("div", { class: "analyst-label", text: "Target price" }),
    NS.el("div", { class: "analyst-value" },
      tgt,
      pct ? NS.el("span", { class: "analyst-value-suffix", text: `(${pct})` }) : null,
    ),
  ));
  sec.append(grid);

  if (total > 0) {
    const frac = (n) => `${(n || 0) / total}fr`;
    const bar = NS.el("div", {
      class: "analyst-bar",
      style: {
        gridTemplateColumns: `${frac(a.strong_buy)} ${frac(a.buy)} ${frac(a.hold)} ${frac(a.sell)} ${frac(a.strong_sell)}`,
      },
    });
    bar.append(
      NS.el("span", { class: "ab-sb" }),
      NS.el("span", { class: "ab-b" }),
      NS.el("span", { class: "ab-h" }),
      NS.el("span", { class: "ab-s" }),
      NS.el("span", { class: "ab-ss" }),
    );
    sec.append(bar);

    const legend = NS.el("div", { class: "analyst-legend" });
    const parts = [
      [a.strong_buy, "Strong Buy"], [a.buy, "Buy"], [a.hold, "Hold"],
      [a.sell, "Sell"], [a.strong_sell, "Strong Sell"],
    ];
    parts.forEach(([n, lbl], i) => {
      if (i > 0) legend.append(NS.el("span", { class: "sep", text: "·" }));
      legend.append(NS.el("span", { class: "num", text: String(n || 0) }));
      legend.append(document.createTextNode(" " + lbl));
    });
    sec.append(legend);
  }
  return sec;
};

/* ----------------------------------------------------------------- holders */
NS.renderHolders = function renderHolders(holders) {
  if (!holders || holders.length === 0) return null;
  const sec = NS.sectionHead("Top institutional holders");
  const table = NS.el("table", { class: "holders-table" });
  const tbody = NS.el("tbody");
  for (const h of holders) {
    const pct = (typeof h.pct === "number") ? `${h.pct.toFixed(2)} %` : "—";
    const chg = (typeof h.change_pct === "number")
      ? `${h.change_pct >= 0 ? "+" : ""}${h.change_pct.toFixed(2)} %`
      : "—";
    const chgCls = (typeof h.change_pct === "number")
      ? (h.change_pct >= 0 ? "h-chg pos" : "h-chg neg")
      : "h-chg";
    const tr = NS.el("tr",
      {},
      NS.el("td", { class: "h-rank", text: String(h.rank) }),
      NS.el("td", { class: "h-name", text: h.name }),
      NS.el("td", { class: "h-pct",  text: pct }),
      NS.el("td", { class: chgCls,   text: chg }),
    );
    tbody.append(tr);
  }
  table.append(tbody);
  sec.append(table);
  return sec;
};

/* ----------------------------------------------------------------- insider */
NS.renderInsider = function renderInsider(insider, currency) {
  if (!insider || insider.length === 0) return null;
  const sec = NS.sectionHead("Recent insider activity");
  const table = NS.el("table", { class: "insider-table" });
  const tbody = NS.el("tbody");
  for (const t of insider) {
    const sideCls = (t.side === "BUY") ? "ins-side buy"
                  : (t.side === "SELL") ? "ins-side sell"
                  : "ins-side";
    const amt = (typeof t.amount === "number") ? t.amount.toLocaleString() : "—";
    const px = (typeof t.price === "number")
      ? `${NS.cursym(currency)}${t.price.toFixed(2)}` : "—";
    tbody.append(NS.el("tr", {},
      NS.el("td", { text: t.date || "—" }),
      NS.el("td", { class: "ins-name", text: t.owner }),
      NS.el("td", { class: sideCls, text: t.side || "—" }),
      NS.el("td", { text: amt + (amt !== "—" ? " sh" : "") }),
      NS.el("td", { text: px }),
    ));
  }
  table.append(tbody);
  sec.append(table);
  return sec;
};

/* ----------------------------------------------------------------- earnings */
NS.renderEarnings = function renderEarnings(history, next, currency) {
  if ((!history || history.length === 0) && !next) return null;
  const sec = NS.sectionHead("Earnings");
  if (history && history.length > 0) {
    const table = NS.el("table", { class: "earnings-table" });
    const head = NS.el("thead");
    head.append(NS.el("tr", {},
      NS.el("th", { class: "e-period", text: "" }),
      NS.el("th", { text: "Reported" }),
      NS.el("th", { text: "Estimate" }),
      NS.el("th", { text: "Surprise" }),
    ));
    table.append(head);
    const tbody = NS.el("tbody");
    for (const r of history) {
      const surpCls = (typeof r.surprise_pct === "number")
        ? (r.surprise_pct >= 0 ? "surprise pos" : "surprise neg")
        : "surprise";
      const surpTxt = (typeof r.surprise_pct === "number")
        ? `${r.surprise_pct >= 0 ? "+" : ""}${r.surprise_pct.toFixed(1)} %`
        : "—";
      const actual = (typeof r.actual === "number") ? r.actual.toFixed(2) : "—";
      const est = (typeof r.estimate === "number") ? r.estimate.toFixed(2) : "—";
      tbody.append(NS.el("tr", {},
        NS.el("td", { class: "e-period", text: r.report_date || r.period }),
        NS.el("td", { text: actual }),
        NS.el("td", { text: est }),
        NS.el("td", { class: surpCls, text: surpTxt }),
      ));
    }
    table.append(tbody);
    sec.append(table);
  }
  if (next && (next.report_date || next.period)) {
    const ne = NS.el("div", { class: "next-earnings" },
      "Next report",
      NS.el("span", { class: "ne-date", text: next.report_date || next.period }),
      next.timing ? document.createTextNode(` · ${next.timing}`) : null,
    );
    sec.append(ne);
  }
  return sec;
};

/* ----------------------------------------------------------------- intelligence */
NS.renderIntelligence = function renderIntelligence(intel) {
  if (!intel || !intel.symbol) return null;
  const sec = NS.sectionHead(
    "Intelligence",
    intel.researched_at
      ? `Researched ${(intel.researched_at || "").slice(0, 10)} · confidence ${intel.confidence || "low"}`
      : null,
  );

  if (intel.confidence_note) {
    sec.append(NS.el("p", { class: "intel-note", text: intel.confidence_note }));
  }

  // Headline lede
  if (intel.one_liner) {
    sec.append(NS.el("p", { class: "intel-lede", text: intel.one_liner }));
  }

  // ---- block: business model + customers + revenue geography
  const overview = [];
  if (intel.business_model) overview.push(["Business model", intel.business_model]);
  if (intel.customers) overview.push(["Customers", intel.customers]);
  if (intel.revenue_geography) overview.push(["Revenue geography", intel.revenue_geography]);
  if (intel.market_position) overview.push(["Market position", intel.market_position]);
  if (intel.industry_trend) overview.push(["Industry trend", intel.industry_trend]);
  if (intel.moat) overview.push(["Moat", intel.moat]);
  if (overview.length > 0) {
    const dl = NS.el("dl", { class: "intel-block" });
    for (const [label, value] of overview) {
      dl.append(NS.el("dt", { text: label }));
      dl.append(NS.el("dd", { text: value }));
    }
    sec.append(dl);
  }

  // ---- products / services
  if ((intel.products_services || []).length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Products & services" }));
    const ul = NS.el("ul", { class: "intel-list" });
    for (const item of intel.products_services) ul.append(NS.el("li", { text: item }));
    sec.append(ul);
  }

  // ---- competitors
  if ((intel.competitors || []).length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Competitors" }));
    const ul = NS.el("ul", { class: "intel-list" });
    for (const c of intel.competitors) {
      ul.append(NS.el("li",
        { class: "intel-comp" },
        NS.el("span", { class: "intel-comp-name", text: c.name }),
        c.note ? NS.el("span", { class: "intel-comp-note", text: " — " + c.note }) : null,
      ));
    }
    sec.append(ul);
  }

  // ---- corporate facts (table)
  const facts = [];
  if (intel.founded) facts.push(["Founded", String(intel.founded)]);
  if (intel.headquarters) facts.push(["Headquarters", intel.headquarters]);
  if (intel.employees) facts.push(["Employees", Number(intel.employees).toLocaleString()]);
  if ((intel.notable_investors || []).length > 0)
    facts.push(["Notable investors", intel.notable_investors.join(", ")]);
  if (facts.length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Corporate" }));
    const dl = NS.el("dl", { class: "intel-block" });
    for (const [label, value] of facts) {
      dl.append(NS.el("dt", { text: label }));
      dl.append(NS.el("dd", { text: value }));
    }
    sec.append(dl);
  }

  // ---- key people
  if ((intel.key_people || []).length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Key people" }));
    const ul = NS.el("ul", { class: "intel-list intel-people" });
    for (const p of intel.key_people) {
      ul.append(NS.el("li", {},
        NS.el("span", { class: "intel-person-name", text: p.name }),
        NS.el("span", { class: "intel-person-role", text: " · " + (p.role || "—") }),
        p.background ? NS.el("div", { class: "intel-person-bio", text: p.background }) : null,
      ));
    }
    sec.append(ul);
  }

  // ---- bull / bear / red flags / catalysts (4-quadrant grid)
  const bull = intel.bull_points || [];
  const bear = intel.bear_points || [];
  const red  = intel.red_flags || [];
  const cat  = intel.catalysts || [];
  if (bull.length || bear.length || red.length || cat.length) {
    const grid = NS.el("div", { class: "intel-quad" });
    grid.append(makeListPanel("Bull case", bull, "intel-bull"));
    grid.append(makeListPanel("Bear case", bear, "intel-bear"));
    grid.append(makeListPanel("Red flags", red, "intel-red"));
    grid.append(makeListPanel("Catalysts", cat, "intel-cat"));
    sec.append(grid);
  }

  // ---- recent news
  if ((intel.recent_news || []).length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Recent news" }));
    const ul = NS.el("ul", { class: "intel-news" });
    for (const n of intel.recent_news) {
      const date = NS.el("span", { class: "intel-news-date", text: n.date });
      const head = n.url
        ? NS.el("a", { class: "intel-news-head", href: n.url, target: "_blank", rel: "noopener", text: n.headline })
        : NS.el("span", { class: "intel-news-head", text: n.headline });
      const src = n.source
        ? NS.el("span", { class: "intel-news-source", text: " · " + n.source })
        : null;
      ul.append(NS.el("li", {}, date, head, src));
    }
    sec.append(ul);
  }

  // ---- sources (citations)
  if ((intel.sources || []).length > 0) {
    sec.append(NS.el("h4", { class: "intel-h", text: "Sources" }));
    const ul = NS.el("ul", { class: "intel-sources" });
    for (const url of intel.sources) {
      ul.append(NS.el("li", {},
        NS.el("a", { href: url, target: "_blank", rel: "noopener", text: shortUrl(url) }),
      ));
    }
    sec.append(ul);
  }

  return sec;
};

function makeListPanel(title, items, modCls) {
  const panel = NS.el("div", { class: "intel-quad-cell " + modCls });
  panel.append(NS.el("div", { class: "intel-quad-title", text: title }));
  if (items.length === 0) {
    panel.append(NS.el("div", { class: "intel-quad-empty", text: "—" }));
  } else {
    const ul = NS.el("ul", { class: "intel-list" });
    for (const it of items) ul.append(NS.el("li", { text: it }));
    panel.append(ul);
  }
  return panel;
}

function shortUrl(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "") + (u.pathname.length > 1 ? u.pathname : "");
  } catch { return url; }
}

/* ----------------------------------------------------------------- splits / dividends */
NS.renderSplitsDivs = function renderSplitsDivs(sd, currency) {
  if (!sd) return null;
  const splits = sd.splits || [];
  const divs = sd.dividends || [];
  if (splits.length === 0 && divs.length === 0) return null;

  const sec = NS.sectionHead("Splits & dividends");
  const grid = NS.el("div", { class: "sd-grid" });

  const splitsCol = NS.el("div", { class: "sd-col" }, NS.el("h4", { text: "Splits" }));
  if (splits.length === 0) splitsCol.append(NS.el("div", { class: "sd-row" }, NS.el("span", { class: "sd-date", text: "no recent splits" })));
  for (const s of splits) {
    splitsCol.append(NS.el("div", { class: "sd-row" },
      NS.el("span", { class: "sd-date", text: s.date }),
      NS.el("span", { class: "sd-amt", text: s.ratio }),
      NS.el("span", {}),
    ));
  }

  const divCol = NS.el("div", { class: "sd-col" }, NS.el("h4", { text: "Dividends" }));
  if (divs.length === 0) divCol.append(NS.el("div", { class: "sd-row" }, NS.el("span", { class: "sd-date", text: "no recent dividends" })));
  for (const d of divs) {
    divCol.append(NS.el("div", { class: "sd-row" },
      NS.el("span", { class: "sd-date", text: d.date }),
      NS.el("span", { class: "sd-amt", text: `${NS.cursym(d.currency || currency)}${d.amount.toFixed(4)}` }),
      NS.el("span", {}),
    ));
  }

  grid.append(splitsCol, divCol);
  sec.append(grid);
  return sec;
};
