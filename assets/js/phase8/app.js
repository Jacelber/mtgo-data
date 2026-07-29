"use strict";

const ReviewData = globalThis.P8ReviewData;
const Runtime = globalThis.P8Runtime;
const I18n = globalThis.P8I18n;
const MtgoController = globalThis.P8MtgoController;
const TabletopController = globalThis.P8TabletopController;
const ENTRY_SURFACE = document.documentElement.dataset.surface || "review";
const PRODUCT_ORDER = [
  "mtgo-statistics",
  "mtgo-matchups",
  "mtgo-top8",
  "tabletop-major-events",
  "weekly-pickup",
];
const PRODUCT_LABEL_KEYS = {
  "mtgo-statistics": "product.stats",
  "mtgo-matchups": "product.matchups",
  "mtgo-top8": "product.top8",
  "tabletop-major-events": "product.tabletop",
  "weekly-pickup": "product.pickup",
};
const FORMAT_LABEL_KEYS = {
  standard: "format.standard",
  pauper: "format.pauper",
  modern: "format.modern",
  pioneer: "format.pioneer",
  legacy: "format.legacy",
  vintage: "format.vintage",
};
const RANGE_OPTIONS = [1, 4, 12];
const DIFF_MIN = 1;
const LOW_SAMPLE_THRESHOLD = 20;
const PIE_COLORS = [
  "#244968", "#2f6288", "#3f77a3", "#568eb8", "#70a4ca",
  "#91bddb", "#a9cde5", "#8f6a2e", "#aa8038", "#c39745",
  "#d5ad5b", "#e0bf78", "#625783", "#766a98", "#8b80aa",
  "#a198bc", "#3f705f", "#588876", "#73a08d", "#93b6a6",
];
const state = {
  catalog: null,
  format: "modern",
  product: "mtgo-statistics",
  statsRange: 1,
  matchupRange: 4,
  statsSort: "high_score_share",
  statsDirection: "desc",
  statsExpanded: new Set(),
  matchupRows: new Set(),
  matchupColumns: new Set(),
  detailIdentity: null,
  detailMode: "average",
  top8WeekFile: null,
  top8Detail: null,
  pickupWeekFile: null,
  pickupOpen: new Set(),
  tabletopView: "overview",
  tabletopEventId: null,
  tabletopSelectedEvents: new Set(),
  tabletopScope: "all_constructed",
  tabletopExpanded: new Set(),
  tabletopDetailIdentity: null,
  tabletopSort: "deck_count",
  tabletopDirection: "desc",
  renderToken: 0,
};
let currentContext = {};

function t(key, values) {
  return I18n.t(key, values);
}

function productLabel(productId) {
  return t(PRODUCT_LABEL_KEYS[productId] || productId);
}

function formatLabel(formatId, fallback = formatId) {
  const key = FORMAT_LABEL_KEYS[formatId];
  return key ? t(key) : fallback;
}

function surfaceProductAvailable(productId, catalogAvailable) {
  if (ENTRY_SURFACE === "mtgo" && productId === "tabletop-major-events") {
    return false;
  }
  return Boolean(catalogAvailable);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pct(value, digits = 1) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? "—"
    : `${(Number(value) * 100).toFixed(digits)}%`;
}

function number(value, digits = 2) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? "—"
    : Number(value).toFixed(digits);
}

function dateText(value) {
  if (!value) return "—";
  return String(value).replace("T", " ").replace(/(\.\d+)?([+-]\d\d:\d\d|Z)$/, "");
}

function formatEntry() {
  return state.catalog.formats.find(item => item.id === state.format);
}

function productEntry(productId = state.product) {
  return formatEntry()?.products.find(item => item.id === productId);
}

function availableProductIds(formatId) {
  return state.catalog.formats
    .find(item => item.id === formatId)
    ?.products.filter(item => surfaceProductAvailable(item.id, item.available))
    .map(item => item.id) || [];
}

function setMessage(text) {
  const node = document.querySelector("#availability-message");
  node.textContent = text;
  node.hidden = !text;
}

function infoTip(text) {
  const safe = escapeHtml(text);
  return `<span class="tip" tabindex="0" aria-label="${safe}" data-tip="${safe}">i</span>`;
}

function rangeButtons(selected, attribute) {
  return `<div class="range-buttons" aria-label="${t("range.label")}">${RANGE_OPTIONS.map(range => (
    `<button type="button" class="${selected === range ? "active" : ""}" ${attribute}="${range}">${t("range.weeks", { count: range })}</button>`
  )).join("")}</div>`;
}

function fixedColumns(count) {
  return `<colgroup><col class="identity-column">${Array.from(
    { length: count - 1 },
    () => '<col class="metric-column">'
  ).join("")}</colgroup>`;
}

function renderNavigation() {
  const formatRoot = document.querySelector("#format-tabs");
  const productRoot = document.querySelector("#product-tabs");
  formatRoot.innerHTML = state.catalog.formats.map(format => {
    const available = format.products.some(item => (
      surfaceProductAvailable(item.id, item.available)
    ));
    return `<button type="button" data-format="${escapeHtml(format.id)}"
      class="${state.format === format.id ? "active" : ""} ${available ? "" : "unavailable"}"
      aria-pressed="${state.format === format.id}" aria-disabled="${!available}"
      title="${available ? "" : t("availability.developing")}">${formatLabel(format.id, escapeHtml(format.display_name))}</button>`;
  }).join("");
  productRoot.innerHTML = PRODUCT_ORDER.map(productId => {
    const available = surfaceProductAvailable(
      productId,
      productEntry(productId)?.available
    );
    return `<button type="button" data-product="${productId}"
      class="${state.product === productId ? "active" : ""} ${available ? "" : "unavailable"}"
      aria-pressed="${state.product === productId}" aria-disabled="${!available}"
      title="${available ? "" : t("availability.developing")}">${productLabel(productId)}</button>`;
  }).join("");
}

function cardLink(card) {
  const name = card.name;
  const quantity = card.qty ?? card.mean_qty ?? "";
  const search = `https://scryfall.com/search?q=${encodeURIComponent(`!"${name}"`)}`;
  const image = `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=image&version=normal`;
  const rate = card.rate === undefined ? "" : ` <small>(${pct(card.rate)})</small>`;
  return `<li><span class="qty">${escapeHtml(quantity)}</span><a class="card-link"
    href="${search}" target="_blank" rel="noopener"
    data-card-image="${escapeHtml(image)}">${escapeHtml(name)}</a>${rate}</li>`;
}

function cardList(cards) {
  if (!cards?.length) return `<p class="empty-state">${t("empty.cards")}</p>`;
  return `<ul class="card-list">${cards.map(cardLink).join("")}</ul>`;
}

function differenceList(items) {
  const visible = (items || []).filter(item => (
    Math.abs(Number(item.deck_qty) - Number(item.typical_qty)) >= DIFF_MIN
  ));
  if (!visible.length) {
    return `<p>${t("deck.difference_none", { count: DIFF_MIN })}</p>`;
  }
  return visible.slice(0, 8).map(item => (
    `<p>${t("deck.difference_row", {
      name: escapeHtml(item.name),
      deck: escapeHtml(item.deck_qty),
      average: escapeHtml(item.typical_qty),
    })}</p>`
  )).join("");
}

function averageDeckHtml(average) {
  if (!average) return `<p class="empty-state">${t("deck.no_average")}</p>`;
  if (state.detailMode === "typical") {
    const medoid = average.medoid;
    if (!medoid) return `<p class="empty-state">${t("deck.no_typical")}</p>`;
    return `<p class="deck-meta">${escapeHtml(medoid.player)} · ${t("deck.rank")} ${escapeHtml(medoid.final_rank)}
      · ${dateText(medoid.starttime)}</p><h4>${t("deck.main")}</h4>${cardList(medoid.main_deck)}
      <h4>${t("deck.side")}</h4>${cardList(medoid.side_deck || medoid.sideboard)}`;
  }
  const reasonText = {
    nobase: t("deck.no_base"),
    recent: t("deck.no_recent"),
    prior: t("deck.no_prior"),
  }[average.recent_change_reason] || "";
  if (!average.sample_size) {
    return `<p class="empty-state">${reasonText || t("deck.no_average_base")}</p>`;
  }
  return `<div class="change-box"><span>${t("deck.recent_change")}</span>
      <strong>${average.recent_change === null || average.recent_change === undefined
        ? t("deck.unavailable")
        : t("deck.points", { count: average.recent_change })}</strong>
      <p>${t("deck.change_help")}</p>
      ${reasonText ? `<p>${escapeHtml(reasonText)}</p>` : ""}
    </div>
    <h4 class="group-title core">${t("deck.core")}</h4>${cardList(average.core)}
    <h4 class="group-title flex">${t("deck.flex")}</h4>${cardList(average.flex)}`;
}

function deckDetailHtml({
  title,
  exactDeck,
  bestDeck,
  averageDeck,
  comparison,
  closeAction,
  exactDeckTitle = t("deck.exact"),
  referenceNote = "",
  performanceHtml = "",
  showDeviation = true,
}) {
  const deck = exactDeck || bestDeck;
  const deckTitle = exactDeck ? exactDeckTitle : t("deck.best");
  const baseStatus = comparison?.base_status;
  const deviation = deck?.deviation;
  const diff = deck?.deviation_diff;
  return `<section class="deck-detail">
    <button class="deck-close" type="button" ${closeAction} aria-label="${t("deck.close")}">✕</button>
    <h3>${escapeHtml(title)}</h3>
    ${baseStatus === "unavailable" ? `<p class="detail-status">${t("deck.comparison_unavailable")}</p>` : ""}
    <div class="deck-columns">
      <div class="deck-column">
        <h4>${deckTitle}</h4>
        ${deck ? `<p class="deck-meta">${escapeHtml(deck.player)} · ${t("deck.rank")} ${escapeHtml(deck.final_rank ?? comparison?.rank ?? "—")}
          · ${dateText(deck.starttime || comparison?.date)}</p>
          ${performanceHtml}
          ${showDeviation ? `<div class="deviation-box"><span>${t("deck.deviation")}</span><strong>${t("deck.points", { count: deviation ?? "—" })}</strong>
            <p>${t("deck.deviation_help", { count: DIFF_MIN })}</p>
            ${diff ? `<div class="difference-grid"><div><b>${t("deck.fewer")}</b>${differenceList(diff.fewer)}</div>
              <div><b>${t("deck.more")}</b>${differenceList(diff.more)}</div></div>` : ""}
          </div>` : ""}<h4>${t("deck.main")}</h4>${cardList(deck.main_deck)}
          <h4>${t("deck.side")}</h4>${cardList(deck.side_deck || deck.sideboard)}` : `<p class="empty-state">${t("empty.deck")}</p>`}
      </div>
      <div class="deck-column">
        ${referenceNote ? `<p class="reference-note">${escapeHtml(referenceNote)}</p>` : ""}
        <div class="deck-mode" role="group" aria-label="${t("deck.average")} / ${t("deck.representative")}">
          <button type="button" data-deck-mode="average" class="${state.detailMode === "average" ? "active" : ""}">${t("deck.average")}</button>
          <button type="button" data-deck-mode="typical" class="${state.detailMode === "typical" ? "active" : ""}">${t("deck.representative")}</button>
          <span>（${t("deck.sample", { count: averageDeck?.sample_size ?? "—" })}）</span>
        </div>
        ${averageDeckHtml(averageDeck)}
      </div>
    </div>
  </section>`;
}

function locateDeck(decksDocument, identityId) {
  for (const value of Object.values(decksDocument.decks || {})) {
    if (value.archetype_id === identityId) {
      return value.subtypes?.length === 1 ? value.subtypes[0] : value;
    }
    const subtype = (value.subtypes || []).find(item => (
      `${item.parent_id}/${item.id}` === identityId
    ));
    if (subtype) return subtype;
  }
  return null;
}

function activeStatisticsSubtypes(parent) {
  return (parent.subtypes || []).filter(subtype => (
    Number(subtype.count) > 0
    || Number(subtype.high_score_count) > 0
    || Number(subtype.top8_count) > 0
    || Number.isFinite(subtype.avg_points_per_round)
  ));
}

function statsRows(archetypes) {
  return archetypes.map(parent => {
    const subtypes = activeStatisticsSubtypes(parent);
    const expandable = subtypes.length >= 2;
    const open = expandable && state.statsExpanded.has(parent.id);
    const directId = subtypes.length === 1
      ? `${parent.id}/${subtypes[0].id}`
      : parent.id;
    const parentName = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-stats-toggle="${escapeHtml(parent.id)}">
          <span class="round-toggle">${open ? "−" : "+"}</span><span class="identity-label">${escapeHtml(parent.name)}</span></button>`
      : `<button class="name-button" type="button" data-detail-identity="${escapeHtml(directId)}">
          <span class="identity-label">${escapeHtml(parent.name)}</span></button>`;
    const rows = [statsRow(parent, parentName, "")];
    if (!expandable && state.detailIdentity === directId) rows.push(statsDetailRow(directId));
    if (open) {
      subtypes.forEach(subtype => {
        const identityId = `${parent.id}/${subtype.id}`;
        rows.push(statsRow(
          subtype,
          `<button class="name-button" type="button" data-detail-identity="${escapeHtml(identityId)}">
            <span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
          "subtype-row"
        ));
        if (state.detailIdentity === identityId) rows.push(statsDetailRow(identityId));
      });
    }
    return rows.join("");
  }).join("");
}

function statsRow(record, nameHtml, rowClass) {
  return `<tr class="${rowClass}">
    <td class="identity-cell">${nameHtml}</td>
    <td class="number">${number(record.avg_points_per_round)}</td>
    <td class="number">${record.high_score_count ?? 0}</td>
    <td class="number">${pct(record.high_score_share)}</td>
    <td class="number">${record.top8_count ?? 0}</td>
    <td class="number">${pct(record.top8_share)}</td>
    <td class="number">${pct(record.conversion)}</td>
  </tr>`;
}

function statsDetailRow(identityId) {
  const record = locateDeck(currentContext.decks, identityId);
  const title = record?.display_name || record?.name || currentContext.identityNames?.get(identityId) || identityId;
  return `<tr class="deck-detail-row"><td colspan="7">${deckDetailHtml({
    title,
    bestDeck: record?.best_deck,
    averageDeck: record?.average_deck,
    closeAction: "data-close-detail",
  })}</td></tr>`;
}

function piePoint(percent, radius = 88) {
  const angle = (percent * 3.6 - 90) * Math.PI / 180;
  return {
    x: 100 + radius * Math.cos(angle),
    y: 100 + radius * Math.sin(angle),
  };
}

function piePath(startPercent, endPercent) {
  const start = piePoint(startPercent);
  const end = piePoint(endPercent >= 100 ? 99.9999 : endPercent);
  const largeArc = endPercent - startPercent > 50 ? 1 : 0;
  return `M 100 100 L ${start.x.toFixed(3)} ${start.y.toFixed(3)}
    A 88 88 0 ${largeArc} 1 ${end.x.toFixed(3)} ${end.y.toFixed(3)} Z`;
}

function pieChart(archetypes, key, label) {
  const countKey = key === "high_score_share" ? "high_score_count" : "top8_count";
  const sorted = [...archetypes].sort((a, b) => (b[key] || 0) - (a[key] || 0));
  const visible = sorted.filter(item => Number(item[key]) > 0.02);
  const remainder = sorted.filter(item => Number(item[key]) <= 0.02)
    .reduce((sum, item) => sum + (Number(item[key]) || 0), 0);
  const remainderCount = sorted.filter(item => Number(item[key]) <= 0.02)
    .reduce((sum, item) => sum + (Number(item[countKey]) || 0), 0);
  const slices = remainder > 0
    ? [...visible, { name: t("chart.other"), [key]: remainder, [countKey]: remainderCount, other: true }]
    : visible;
  let cursor = 0;
  const segments = slices.map((item, index) => {
    const start = cursor;
    cursor += (Number(item[key]) || 0) * 100;
    const color = item.other ? "#c7ccd1" : PIE_COLORS[index % PIE_COLORS.length];
    const detail = `${item.name} · ${pct(item[key])} · ${t("chart.decks", { count: Number(item[countKey]) || 0 })}`;
    return `<path class="pie-slice" d="${piePath(start, cursor)}" fill="${color}"
      tabindex="0" data-pie-detail="${escapeHtml(detail)}" aria-label="${escapeHtml(detail)}">
      <title>${escapeHtml(detail)}</title></path>`;
  });
  if (cursor < 99.999) {
    segments.push(`<path class="pie-slice pie-slice-unavailable" d="${piePath(cursor, 100)}" fill="#eef0f2"
      tabindex="0" data-pie-detail="${t("chart.unassigned")} · ${(100 - cursor).toFixed(1)}% · ${t("chart.decks", { count: 0 })}"
      aria-label="${t("chart.unassigned")} · ${(100 - cursor).toFixed(1)}% · ${t("chart.decks", { count: 0 })}"></path>`);
  }
  const legend = slices.map((item, index) => (
    `<li><i style="background:${item.other ? "#c7ccd1" : PIE_COLORS[index % PIE_COLORS.length]}"></i>
      <span>${escapeHtml(item.name)}</span><strong>${pct(item[key])}</strong>
      <small>${t("chart.count", { count: Number(item[countKey]) || 0 })}</small></li>`
  )).join("");
  return `<article class="pie-card"><h3>${label}</h3><div class="pie-body">
    <div class="pie-chart-shell"><svg class="pie" viewBox="0 0 200 200" role="img" aria-label="${label}">
      ${segments.join("")}</svg>
      <div class="pie-readout" role="status">${t("chart.help")}</div></div>
    <ul class="pie-legend">${legend}</ul></div></article>`;
}

function chartHtml(archetypes) {
  return `<section class="panel pie-panel" aria-label="${t("chart.aria")}">
    ${pieChart(archetypes, "high_score_share", t("stats.high_share"))}
    ${pieChart(archetypes, "top8_share", t("stats.top8_share"))}
  </section>`;
}

function sortedArchetypes(archetypes) {
  const direction = state.statsDirection === "asc" ? 1 : -1;
  return [...archetypes].sort((left, right) => {
    const a = state.statsSort === "name" ? left.name.toLowerCase() : (left[state.statsSort] ?? -1);
    const b = state.statsSort === "name" ? right.name.toLowerCase() : (right[state.statsSort] ?? -1);
    return a < b ? -direction : a > b ? direction : 0;
  });
}

async function statsView() {
  const { meta, range, decks, completeness } = await MtgoController
    .loadStatistics(state.format, state.statsRange);
  const archetypes = sortedArchetypes(range.archetypes);
  const identityNames = new Map();
  range.archetypes.forEach(parent => {
    identityNames.set(parent.id, parent.name);
    (parent.subtypes || []).forEach(subtype => identityNames.set(`${parent.id}/${subtype.id}`, subtype.display_name));
  });
  currentContext = { meta, range, decks, completeness, identityNames };
  const hs = completeness.high_score_decklist_completeness;
  const expandable = range.archetypes.filter(item => activeStatisticsSubtypes(item).length >= 2);
  const sortHeader = (label, key, tip) => {
    const arrow = state.statsSort === key ? (state.statsDirection === "desc" ? " ▼" : " ▲") : "";
    return `<button class="sort-button" type="button" data-stats-sort="${key}">${label}${arrow}</button>${tip ? infoTip(tip) : ""}`;
  };
  return `<section class="source-note">
      <p>${t("source.stats")}</p>
      <p>${t("stats.updated", {
        rules: dateText(meta.rules_updated),
        data: dateText(meta.data_updated),
      })}</p>
    </section>
    ${rangeButtons(state.statsRange, "data-stats-range")}
    <div class="period-info">
      <span>${t("stats.period", {
        start: range.period.start,
        end: range.period.end,
        decks: range.total_decks,
        high: range.total_high_score,
        top8: range.total_top8,
      })}</span>
      <strong>${t("stats.completeness", {
        observed: hs.observed_decklist_count,
        expected: hs.expected_decklist_count_display ?? hs.expected_decklist_count,
        rate: pct(hs.completeness_rate),
      })}</strong>
    </div>
    ${chartHtml(archetypes)}
    <section class="panel">
      <div class="panel-toolbar"><h2>${t("stats.title")}</h2>
        ${expandable.length ? `<button id="stats-expand-all" class="secondary-button" type="button">${state.statsExpanded.size ? t("stats.hide_subtypes") : t("stats.show_subtypes")}</button>` : ""}
      </div>
      <p class="real-data-note">${t("stats.note")}</p>
      <div class="table-scroll"><table class="data-table metric-columns" style="width:980px;min-width:100%">
        ${fixedColumns(7)}
        <thead><tr><th>${sortHeader(t("stats.deck"), "name")}</th>
          <th class="number">${sortHeader(t("stats.average_points"), "avg_points_per_round", t("stats.average_points_tip"))}</th>
          <th class="number">${sortHeader(t("stats.high_count"), "high_score_count")}</th>
          <th class="number">${sortHeader(t("stats.high_share"), "high_score_share")}</th>
          <th class="number">${sortHeader(t("stats.top8_count"), "top8_count")}</th>
          <th class="number">${sortHeader(t("stats.top8_share"), "top8_share")}</th>
          <th class="number">${sortHeader(t("stats.conversion"), "conversion", t("stats.conversion_tip"))}</th>
        </tr></thead><tbody>${statsRows(archetypes)}</tbody>
      </table></div>
    </section>`;
}

function matchupLegend(lowSampleThreshold) {
  const lowSampleText = Number.isFinite(lowSampleThreshold)
    ? t("matchup.low_sample", { count: lowSampleThreshold })
    : t("matchup.threshold_pending");
  return `<div class="matchup-legend">
    <span>${t("matchup.colors")}</span><div><div class="legend-bar"></div>
      <div class="legend-values"><span>0%</span><span>50%</span><span>100%</span></div></div>
    <span><i class="na-chip"></i>${t("matchup.none")}</span><span><i class="low-chip"></i>${lowSampleText}</span>
  </div>`;
}

function mixColor(from, to, ratio) {
  const channel = index => Math.round(from[index] + (to[index] - from[index]) * ratio);
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

function winRateColor(rate) {
  const red = [191, 86, 76];
  const yellow = [232, 200, 74];
  const green = [57, 137, 87];
  return rate <= 0.5
    ? mixColor(red, yellow, Math.max(0, rate) * 2)
    : mixColor(yellow, green, Math.min(1, (rate - 0.5) * 2));
}

function matrixCell(record) {
  if (!record || record.win_rate === null) return `<td class="matrix-cell na" title="${t("matchup.none")}">—</td>`;
  const low = record.low_sample ? "low-sample" : "";
  const ci = record.confidence_interval_95;
  const half = ci ? ((ci.upper - ci.lower) / 2) : null;
  const recordText = `${record.wins}-${record.losses}-${record.draws}（${record.matches}）`;
  const foreground = record.win_rate < 0.2 || record.win_rate > 0.72 ? "#fff" : "#26313a";
  return `<td class="matrix-cell ${low}" tabindex="0"
    style="background:${winRateColor(record.win_rate)};color:${foreground}"
    data-record="${recordText}" title="${t("matchup.record", { record: recordText })}${record.mirror ? ` · ${t("matchup.mirror")}` : ""}">
    <strong>${(record.win_rate * 100).toFixed(1)}</strong><small>${half === null ? "—" : `±${(half * 100).toFixed(1)}`}</small></td>`;
}

function matrixHtml(document) {
  const view = ReviewData.buildView(document, state.matchupRows, state.matchupColumns);
  return `<div class="table-scroll matrix-scroll"><table class="matchup-table">
    <thead><tr><th class="corner"></th><th class="column-head overall">${t("matchup.overall")}</th>
      ${view.columns.map(column => {
        const open = state.matchupColumns.has(column.parentId);
        const content = column.kind === "archetype" && column.expandable
          ? `<button type="button" class="axis-label-button column-axis-label" data-matchup-column="${escapeHtml(column.parentId)}"
              aria-label="${open ? t("matchup.collapse") : t("matchup.expand")}${escapeHtml(column.name)}" title="${escapeHtml(column.name)}">
              <span class="axis-toggle">${open ? "−" : "+"}</span><span class="axis-name">${escapeHtml(column.name)}</span></button>`
          : `<span>${escapeHtml(column.name)}</span>`;
        return `<th class="column-head ${column.kind === "subtype" ? "subtype-head" : ""}"><div>${content}</div></th>`;
      }).join("")}
    </tr></thead><tbody>
      ${view.rows.map(row => {
        const open = state.matchupRows.has(row.parentId);
        const content = row.kind === "archetype" && row.expandable
          ? `<button type="button" class="axis-label-button row-axis-label" data-matchup-row="${escapeHtml(row.parentId)}"
              aria-label="${open ? t("matchup.collapse") : t("matchup.expand")}${escapeHtml(row.name)}">
              <span class="axis-toggle">${open ? "−" : "+"}</span><span>${escapeHtml(row.name)}</span></button>`
          : `<span>${escapeHtml(row.name)}</span>`;
        return `<tr><th class="row-head ${row.kind === "subtype" ? "subtype-head" : ""}">${content}</th>
          ${matrixCell(view.overall[row.id])}${view.columns.map(column => matrixCell(view.matrix[row.id][column.id])).join("")}</tr>`;
      }).join("")}
    </tbody></table></div><div id="matrix-record" class="matrix-record" role="status" hidden></div>
    <div id="matrix-hover-pop" class="matrix-hover-pop" role="tooltip" hidden></div>`;
}

async function matchupView() {
  const { document, completeness } = await MtgoController
    .loadMatchup(state.format, state.matchupRange);
  const displayDocument = ReviewData.activeMatchupDocument(document, LOW_SAMPLE_THRESHOLD);
  currentContext = { matchupDocument: displayDocument, completeness };
  const coverage = completeness.matchup_coverage;
  return `${rangeButtons(state.matchupRange, "data-matchup-range")}
    <section class="source-note">
      <p>${t("source.matchups")}</p>
      <p><strong>${t("matchup.completeness", {
        expected: coverage.expected_event_count,
        available: coverage.available_event_count,
        rate: pct(coverage.completeness_rate),
        deferred: coverage.deferred_event_count,
        missing: coverage.missing_event_count,
        excluded: coverage.excluded_event_count,
      })}</strong></p>
    </section>
    <section class="panel"><div class="panel-toolbar"><div><h2>${t("matchup.title")}</h2>
      <p class="matrix-toolbar-note">${t("matchup.note")}</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? t("matchup.collapse_all") : t("matchup.expand_all")}</button>
    </div>${matchupLegend(displayDocument.min_sample_hint)}${matrixHtml(displayDocument)}</section>`;
}

function top8PlacementDetail() {
  if (!state.top8Detail) return "";
  const [eventId, rankText] = state.top8Detail.split(":");
  const event = currentContext.top8.events.find(item => item.event_id === eventId);
  const placement = event?.placements.find(item => item.rank === Number(rankText));
  if (!placement) return "";
  const identityId = placement.identity?.identity_id;
  const base = currentContext.bases.identities?.[identityId];
  return deckDetailHtml({
    title: placement.identity?.display_name || t("top8.unknown"),
    exactDeck: placement.exact_deck,
    averageDeck: base?.average_deck,
    comparison: { ...placement.comparison, rank: placement.rank, date: event.date },
    closeAction: "data-close-top8",
  });
}

async function top8View() {
  const indexPath = productEntry().path;
  const { index, weekEntry, top8, bases } = await MtgoController
    .loadTop8(indexPath, state.top8WeekFile);
  state.top8WeekFile = weekEntry.file;
  currentContext = { top8Index: index, top8, bases };
  return `<section class="source-note"><p>${t("source.top8")}</p></section>
    <div class="select-row"><label for="top8-week">${t("top8.week")}</label>
      <select id="top8-week">${index.weeks.map(item => (
        `<option value="${escapeHtml(item.file)}" ${item.file === state.top8WeekFile ? "selected" : ""}>${item.start} ～ ${item.end}</option>`
      )).join("")}</select>
    </div>
    <section class="panel"><p class="real-data-note">${t("top8.summary", {
      events: top8.events.length,
      placements: top8.events.reduce((sum, event) => sum + event.placements.length, 0),
    })}</p>
      <div class="table-scroll"><table class="top8-table top8-week-table"><thead><tr><th>${t("top8.rank")}</th>
        ${top8.events.map(event => `<th title="${escapeHtml(event.name)}"><strong>${escapeHtml(event.display_name)}</strong>
          <small>${event.date} · ${t("top8.players", { count: event.player_count })}</small></th>`).join("")}
      </tr></thead><tbody>${Array.from({ length: 8 }, (_, offset) => {
        const rank = offset + 1;
        return `<tr><td>${rank}</td>${top8.events.map(event => {
          const placement = event.placements.find(item => item.rank === rank);
          if (!placement || placement.deck_status !== "available") return `<td class="missing-deck">${t("top8.unavailable")}</td>`;
          return `<td><button class="name-button" type="button" data-top8-detail="${escapeHtml(event.event_id)}:${rank}">${escapeHtml(placement.identity.display_name)}</button></td>`;
        }).join("")}</tr>`;
      }).join("")}</tbody></table></div>${top8PlacementDetail()}</section>`;
}

function scopeLabel(scope) {
  return {
    day1: "第一日摩登",
    day2: "第二日摩登",
    all_constructed: "全部摩登瑞士轮",
  }[scope] || scope;
}

function eventDateRange(date) {
  if (!date) return "—";
  if (typeof date === "string") return date;
  return date.start === date.end ? date.start : `${date.start} ～ ${date.end}`;
}

function eventStructureLabel(value) {
  return {
    mixed: "混合赛制",
    constructed_day2: "纯构筑 · 有 Cut",
    constructed_single_stage: "纯构筑 · 无 Cut",
  }[value] || value;
}

function qualityStatusLabel(value) {
  return {
    ok: "正常",
    warning: "警告",
    blocked: "阻断",
  }[value] || value;
}

function issueMessage(issue) {
  return {
    unknown_classifications: "有效提交的牌表中仍有明确保留为 Unknown 的记录。",
    disqualified_participant_matches_excluded: "被取消资格的牌手记录继续留档，其涉及的全部对局从实战统计中对称排除。",
    mixed_event_day2_selection_bias: "第二日参赛者由包含轮抽在内的综合赛事表现筛选；第二日摩登统计描述入围人群。",
    overall_standings_include_non_constructed_results: "最终名次和赛事总积分仅作背景信息，不作为摩登表现积分。",
  }[issue.code] || issue.message;
}

function overviewRecord(record) {
  return record?.literal_record || record;
}

function eventDeckMatchesIdentity(deck, identityId) {
  const [archetypeId, subtypeId] = identityId.split("/");
  return deck.classification?.archetype_id === archetypeId
    && (!subtypeId || deck.classification?.subtype_id === subtypeId);
}

function bestEventDeck(identityId, scopeId) {
  const candidates = (currentContext.tabletopDecks?.decks || []).filter(deck => {
    const scope = deck.scopes?.[scopeId];
    return eventDeckMatchesIdentity(deck, identityId)
      && deck.participant_status !== "disqualified"
      && !deck.statistics_eligibility?.played_match_metrics_excluded
      && deck.decklist?.status === "submitted"
      && deck.decklist?.cards?.length
      && scope?.participated;
  });
  candidates.sort((left, right) => {
    const a = left.scopes[scopeId];
    const b = right.scopes[scopeId];
    return (b.average_points_per_effective_round ?? -1) - (a.average_points_per_effective_round ?? -1)
      || (b.constructed_points ?? -1) - (a.constructed_points ?? -1)
      || (b.played_record?.wins ?? -1) - (a.played_record?.wins ?? -1)
      || String(left.participant_id).localeCompare(String(right.participant_id));
  });
  return candidates[0] || null;
}

function eventDeckForDisplay(deck) {
  if (!deck) return null;
  const cards = deck.decklist.cards || [];
  return {
    player: deck.player_name,
    final_rank: deck.final_rank,
    main_deck: cards.filter(card => card.section === "main").map(card => ({ name: card.name, qty: card.quantity })),
    side_deck: cards.filter(card => card.section === "sideboard").map(card => ({ name: card.name, qty: card.quantity })),
  };
}

function tabletopDetailRow(identityId) {
  const source = bestEventDeck(identityId, state.tabletopScope);
  const exactDeck = eventDeckForDisplay(source);
  const mtgoBase = locateDeck(currentContext.mtgoDecks, identityId);
  const performance = source?.scopes?.[state.tabletopScope];
  const record = performance?.played_record;
  const title = source?.classification?.subtype_name
    ? `${source.classification.subtype_name} ${source.classification.archetype_name}`
    : (source?.classification?.archetype_name || currentContext.tabletopIdentityNames.get(identityId) || identityId);
  const performanceHtml = performance ? `<div class="event-deck-performance">
    <strong>${scopeLabel(state.tabletopScope)}内表现</strong>
    <span>场均分 ${number(performance.average_points_per_effective_round)} · 构筑积分 ${performance.constructed_points}
      · ${record ? `${record.wins}-${record.losses}-${record.draws}` : "无有效对局"}</span>
    <small>按场均分选择；同分依次比较构筑积分和胜场。取消资格牌手不参与选择。</small>
  </div>` : "";
  return `<tr class="deck-detail-row"><td colspan="9">${deckDetailHtml({
    title,
    exactDeck,
    exactDeckTitle: "最佳表现牌表",
    averageDeck: mtgoBase?.average_deck,
    comparison: { date: eventDateRange(currentContext.overview.event.date) },
    closeAction: "data-close-tabletop-detail",
    referenceNote: "右侧来源：MTGO 最近4周平均构筑与典型牌表，仅供构筑参考，不属于该实体赛事统计。",
    performanceHtml,
    showDeviation: false,
  })}</td></tr>`;
}

function tabletopOverall(scope) {
  const counts = {
    wins: scope.result_counts.played_win || 0,
    losses: scope.result_counts.played_loss || 0,
    draws: scope.result_counts.played_draw || 0,
  };
  const record = ReviewData.literalRecord(counts);
  const dropRounds = scope.result_counts.drop_unplayed || 0;
  const completion = scope.theoretical_rounds
    ? (scope.theoretical_rounds - dropRounds) / scope.theoretical_rounds
    : null;
  return {
    name: "整体",
    overall: true,
    deck_count: scope.participant_count,
    metagame_share: 1,
    average_points_per_effective_round: scope.average_points_per_effective_round,
    completion_rate: completion,
    high_score: scope.high_score_deck_count === null ? null : { count: scope.high_score_deck_count },
    literal_record: record,
    subtypes: [],
  };
}

function tabletopRow(record, className = "") {
  const match = record.literal_record || overviewRecord(record.match_record?.all_matches);
  const high = record.high_score?.count;
  return `<tr class="${className}">
    <td class="identity-cell">${record.nameHtml || escapeHtml(record.display_name || record.archetype_name || record.name)}</td>
    <td class="number">${record.deck_count}</td><td class="number">${pct(record.metagame_share)}</td>
    <td class="number">${number(record.average_points_per_effective_round)}</td>
    <td class="number">${pct(match?.win_rate)}</td>
    <td class="number">${match ? `${match.wins}-${match.losses}-${match.draws}` : "—"}</td>
    <td class="number">${match?.matches ?? "—"}</td><td class="number">${pct(record.completion_rate)}</td>
    <td class="number">${high ?? "—"}</td>
  </tr>`;
}

function tabletopSortValue(record, key) {
  if (key === "name") return (record.archetype_name || record.display_name || "").toLowerCase();
  if (key === "win_rate") return overviewRecord(record.match_record?.all_matches)?.win_rate ?? -1;
  if (key === "matches") return overviewRecord(record.match_record?.all_matches)?.matches ?? -1;
  if (key === "high_score") return record.high_score?.count ?? -1;
  return record[key] ?? -1;
}

function sortedTabletopArchetypes(archetypes) {
  const direction = state.tabletopDirection === "asc" ? 1 : -1;
  return [...archetypes].sort((left, right) => {
    const a = tabletopSortValue(left, state.tabletopSort);
    const b = tabletopSortValue(right, state.tabletopSort);
    return a < b ? -direction : a > b ? direction : 0;
  });
}

function activeTabletopSubtypes(parent) {
  return (parent.subtypes || []).filter(subtype => Number(subtype.deck_count) > 0);
}

function tabletopOverview(scope) {
  const identityNames = new Map();
  scope.archetypes.forEach(parent => {
    if (parent.archetype_id) identityNames.set(parent.archetype_id, parent.archetype_name);
    activeTabletopSubtypes(parent).forEach(subtype => {
      identityNames.set(`${parent.archetype_id}/${subtype.subtype_id}`, subtype.display_name);
    });
  });
  currentContext.tabletopIdentityNames = identityNames;
  const rows = sortedTabletopArchetypes(scope.archetypes).map(parent => {
    const subtypes = activeTabletopSubtypes(parent);
    const expandable = subtypes.length >= 2;
    const open = expandable && state.tabletopExpanded.has(parent.archetype_id);
    const parentIdentity = parent.archetype_id;
    const directIdentity = subtypes.length === 1
      ? `${parent.archetype_id}/${subtypes[0].subtype_id}`
      : parentIdentity;
    const nameHtml = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-tabletop-toggle="${escapeHtml(parent.archetype_id)}">
          <span class="round-toggle">${open ? "−" : "+"}</span><span class="identity-label">${escapeHtml(parent.archetype_name)}</span></button>`
      : directIdentity
        ? `<button class="name-button" type="button" data-tabletop-detail="${escapeHtml(directIdentity)}">
            <span class="identity-label">${escapeHtml(parent.archetype_name)}</span></button>`
        : `<span class="identity-label">${escapeHtml(parent.archetype_name)}</span>`;
    const output = [tabletopRow({ ...parent, nameHtml })];
    if (!expandable && directIdentity && state.tabletopDetailIdentity === directIdentity) {
      output.push(tabletopDetailRow(directIdentity));
    }
    if (open) {
      subtypes.forEach(subtype => {
        const identityId = `${parent.archetype_id}/${subtype.subtype_id}`;
        output.push(tabletopRow({
          ...subtype,
          literal_record: overviewRecord(subtype.match_record?.all_matches),
          nameHtml: `<button class="name-button" type="button" data-tabletop-detail="${escapeHtml(identityId)}">
            <span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
        }, "subtype-row"));
        if (state.tabletopDetailIdentity === identityId) output.push(tabletopDetailRow(identityId));
      });
    }
    return output.join("");
  }).join("");
  const sortHeader = (label, key, tip) => {
    const arrow = state.tabletopSort === key ? (state.tabletopDirection === "desc" ? " ▼" : " ▲") : "";
    return `<button class="sort-button" type="button" data-tabletop-sort="${key}">${label}${arrow}</button>${tip ? infoTip(tip) : ""}`;
  };
  return `<div class="panel-toolbar"><h2>套牌表现概览</h2>
      <button id="tabletop-expand-all" class="secondary-button" type="button">${state.tabletopExpanded.size ? "隐藏全部子类型" : "显示全部子类型"}</button>
    </div><div class="table-scroll"><table class="data-table metric-columns" style="width:1250px;min-width:100%">
      ${fixedColumns(9)}<thead><tr><th>${sortHeader("套牌类型", "name")}</th><th class="number">${sortHeader("牌表数", "deck_count")}</th>
        <th class="number">${sortHeader("环境占比", "metagame_share")}</th>
        <th class="number">${sortHeader("场均分", "average_points_per_effective_round", "当前赛事范围内获得的构筑积分 ÷ 有效理论轮数；轮抽积分不计入。")}</th>
        <th class="number">${sortHeader("胜率", "win_rate", "胜场数 ÷ 有效对局数；平局计入分母但不折算为胜场，并包含内战。")}</th><th class="number">胜-负-平</th>
        <th class="number">${sortHeader("有效对局", "matches", "实际进行并计入胜率的构筑瑞士轮对局；轮抽、轮空、约和、未进行轮次及裁定胜不计入。")}</th>
        <th class="number">${sortHeader("完赛率", "completion_rate", "已完成或经赛事结构确认免除的轮数 ÷ 理论应参加轮数；退赛后未进行轮次会降低完赛率。")}</th>
        <th class="number">${sortHeader("高分牌表", "high_score")}</th></tr></thead>
      <tbody>${tabletopRow(tabletopOverall(scope), "overall-row")}${rows}</tbody>
    </table></div>`;
}

function tabletopMatchup(matchupDocument, scopeId) {
  const scope = matchupDocument.scopes[scopeId];
  const viewDocument = ReviewData.activeMatchupDocument({
    hierarchical: true,
    hierarchy: matchupDocument.hierarchy,
    parent_order: scope.parent_order,
    leaf_matrix: scope.leaf_matrix,
  }, LOW_SAMPLE_THRESHOLD);
  currentContext.matchupDisplayDocument = viewDocument;
  return `<div class="panel-toolbar"><div><h2>赛事对阵胜率</h2>
      <p class="matrix-toolbar-note">${scopeLabel(scopeId)} · ${scope.included_match_count} 场有效对局。类型保留，行列可独立展开。</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? "收起全部子类型" : "展开全部子类型"}</button>
    </div>${matchupLegend(viewDocument.min_sample_hint)}${matrixHtml(viewDocument)}`;
}

async function tabletopView() {
  const indexPath = productEntry().path;
  const {
    eventEntry,
    index,
    matchup,
    meta,
    mtgoDecks,
    overview,
    quality,
    tabletopDecks,
  } = await TabletopController.loadEvent(
    indexPath,
    state.tabletopEventId,
    state.format,
    MtgoController
  );
  state.tabletopEventId = eventEntry.event_id;
  state.tabletopSelectedEvents.add(eventEntry.event_id);
  if (!overview.scope_order.includes(state.tabletopScope)) state.tabletopScope = overview.default_scope;
  const scope = overview.scopes[state.tabletopScope];
  currentContext = { tabletopIndex: index, eventEntry, meta, overview, matchup, quality, tabletopDecks, mtgoDecks };
  const viewTabs = `<div class="tabletop-view-tabs subview-tabs" role="group" aria-label="实体大赛视图">
    <button type="button" data-tabletop-view="overview" class="${state.tabletopView === "overview" ? "active" : ""}">赛事概览</button>
    <button type="button" data-tabletop-view="matchup" class="${state.tabletopView === "matchup" ? "active" : ""}">对阵胜率</button>
  </div>`;
  const selector = state.tabletopView === "overview"
    ? `<div class="select-row"><label for="tabletop-event">选择赛事：</label><select id="tabletop-event">${index.events.map(item => (
        `<option value="${escapeHtml(item.event_id)}" ${item.event_id === state.tabletopEventId ? "selected" : ""}>${escapeHtml(item.name)}</option>`
      )).join("")}</select></div>`
    : `<div class="select-row"><span>选择赛事：</span><div class="event-selector-pane">${index.events.map(item => (
        `<label><input type="checkbox" data-tabletop-event-check="${escapeHtml(item.event_id)}"
          ${state.tabletopSelectedEvents.has(item.event_id) ? "checked" : ""}> ${escapeHtml(item.name)}</label>`
      )).join("")}</div></div>`;
  const scopes = `<div class="range-buttons" aria-label="赛事范围">${overview.scope_order.map(scopeId => (
    `<button type="button" data-tabletop-scope="${scopeId}" class="${state.tabletopScope === scopeId ? "active" : ""}">${scopeLabel(scopeId)}</button>`
  )).join("")}</div>`;
  const retainedQualityCodes = new Set([
    "disqualified_participant_matches_excluded",
    "mixed_event_day2_selection_bias",
  ]);
  const issueList = quality.issues.filter(issue => retainedQualityCodes.has(issue.code)).map(issue => (
    issue.code === "disqualified_participant_matches_excluded"
      ? `<li>${quality.counts.disqualified_participant_count} 名被取消资格牌手继续留档；其涉及的
        ${quality.counts.disqualified_matches_excluded} 场对局从实战统计中对称排除。</li>`
      : `<li>${escapeHtml(issueMessage(issue))}</li>`
  )).join("");
  return `${viewTabs}${selector}${scopes}
    <section class="panel event-summary"><div class="event-title-row"><strong>${escapeHtml(overview.event.name)}</strong>
      <a href="${escapeHtml(overview.event.source_url)}" target="_blank" rel="noopener">查看赛事来源</a></div>
      <p>${eventDateRange(overview.event.date)} · ${escapeHtml(eventStructureLabel(overview.event_structure))} · Melee 赛事 ID ${escapeHtml(overview.event_id)}</p>
      <div class="quality-notice"><strong>数据质量说明</strong>
        <ul class="quality-list">${issueList}</ul></div>
    </section>
    <section class="panel">${state.tabletopView === "overview"
      ? tabletopOverview(scope)
      : tabletopMatchup(matchup, state.tabletopScope)}</section>`;
}

function pickupDeck(item, key) {
  const title = key === "existing_changes"
    ? t("pickup.new_tech")
    : t("pickup.new_decks");
  const id = `${key}:${item.archetype}:${item.player}`;
  const open = state.pickupOpen.has(id);
  const comment = I18n.language() === "en"
    ? (item.comment_en || item.comment_zh || "")
    : (item.comment_zh || "");
  return `<article class="pickup-card ${open ? "open" : ""}">
    <button type="button" class="pickup-head" data-pickup-toggle="${escapeHtml(id)}" aria-expanded="${open}">
      <span><strong>${escapeHtml(item.archetype)}</strong><small>${escapeHtml(item.player)} · ${t("deck.rank")} ${item.final_rank}
      · ${t("deck.points", { count: item.swiss_score })} · ${dateText(item.starttime)}</small></span><b>${title} · ${t("deck.deviation")} ${t("deck.points", { count: item.deviation })}</b>
    </button>${open ? `<div class="pickup-body"><p>${escapeHtml(comment)}</p>
      <div class="deck-columns"><div class="deck-column"><h4>${t("deck.main")}</h4>${cardList(item.main_deck)}</div>
      <div class="deck-column"><h4>${t("deck.side")}</h4>${cardList(item.side_deck)}</div></div></div>` : ""}</article>`;
}

async function pickupView() {
  const indexPath = productEntry().path;
  const { index, week, document } = await MtgoController
    .loadPickup(indexPath, state.pickupWeekFile);
  state.pickupWeekFile = week.file;
  currentContext = { pickupIndex: index, pickupDocument: document };
  const groups = [
    [t("pickup.new_tech"), "existing_changes"],
    [t("pickup.new_decks"), "new_archetypes"],
  ];
  return `<section class="source-note"><p>${t("source.pickup")}</p></section>
    <div class="pickup-layout"><aside class="pickup-weeks"><h2>${t("pickup.archive")}</h2>${index.weeks.map(item => (
      `<button type="button" data-pickup-week="${escapeHtml(item.file)}" class="${item.file === state.pickupWeekFile ? "active" : ""}">
        ${escapeHtml(item.week)}<span>${item.start} ～ ${item.end}</span></button>`
    )).join("")}</aside><div class="pickup-content">${groups.map(([title, key]) => (
      `<section class="pickup-group"><h2>${title}</h2>${document[key]?.length
        ? document[key].map(item => pickupDeck(item, key)).join("")
        : `<p class="pickup-empty">${t("pickup.empty")}</p>`}</section>`
    )).join("")}</div></div>`;
}

async function renderView() {
  const root = document.querySelector("#view");
  const token = ++state.renderToken;
  root.innerHTML = `<p class="loading-state">${t("loading.data")}</p>`;
  try {
    let html;
    if (state.product === "mtgo-statistics") html = await statsView();
    else if (state.product === "mtgo-matchups") html = await matchupView();
    else if (state.product === "mtgo-top8") html = await top8View();
    else if (state.product === "tabletop-major-events") html = await tabletopView();
    else html = await pickupView();
    if (token !== state.renderToken) return;
    root.innerHTML = html;
    document.querySelector("#payload-status").textContent = t("loading.loaded", {
      format: formatLabel(state.format),
      product: productLabel(state.product),
    });
  } catch (error) {
    if (token !== state.renderToken) return;
    root.innerHTML = `<p class="error-state"><strong>${t("loading.error")}</strong><br>${escapeHtml(error.message)}</p>`;
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

function resetInteractions() {
  state.statsExpanded.clear();
  state.matchupRows.clear();
  state.matchupColumns.clear();
  state.tabletopExpanded.clear();
  state.detailIdentity = null;
  state.top8Detail = null;
  state.tabletopDetailIdentity = null;
}

document.addEventListener("click", async event => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.format) {
    const next = button.dataset.format;
    const available = availableProductIds(next);
    if (!available.length) {
      setMessage(t("availability.format", { format: formatLabel(next) }));
      return;
    }
    state.format = next;
    if (!available.includes(state.product)) state.product = available[0];
    resetInteractions();
    setMessage("");
    renderNavigation();
    await renderView();
  } else if (button.dataset.product) {
    if (!surfaceProductAvailable(
      button.dataset.product,
      productEntry(button.dataset.product)?.available
    )) {
      setMessage(t("availability.product", {
        format: formatLabel(state.format),
        product: productLabel(button.dataset.product),
      }));
      return;
    }
    state.product = button.dataset.product;
    resetInteractions();
    setMessage("");
    renderNavigation();
    await renderView();
  } else if (button.dataset.statsRange) {
    state.statsRange = Number(button.dataset.statsRange);
    state.detailIdentity = null;
    await renderView();
  } else if (button.dataset.matchupRange) {
    state.matchupRange = Number(button.dataset.matchupRange);
    await renderView();
  } else if (button.dataset.statsToggle) {
    toggleSet(state.statsExpanded, button.dataset.statsToggle);
    state.detailIdentity = null;
    await renderView();
  } else if (button.dataset.statsSort) {
    if (state.statsSort === button.dataset.statsSort) state.statsDirection = state.statsDirection === "desc" ? "asc" : "desc";
    else {
      state.statsSort = button.dataset.statsSort;
      state.statsDirection = state.statsSort === "name" ? "asc" : "desc";
    }
    await renderView();
  } else if (button.id === "stats-expand-all") {
    const expandable = currentContext.range.archetypes.filter(item => activeStatisticsSubtypes(item).length >= 2);
    if (state.statsExpanded.size) state.statsExpanded.clear();
    else expandable.forEach(item => state.statsExpanded.add(item.id));
    state.detailIdentity = null;
    await renderView();
  } else if (button.dataset.detailIdentity) {
    state.detailIdentity = state.detailIdentity === button.dataset.detailIdentity
      ? null
      : button.dataset.detailIdentity;
    state.detailMode = "average";
    await renderView();
  } else if (button.hasAttribute("data-close-detail")) {
    state.detailIdentity = null;
    await renderView();
  } else if (button.dataset.deckMode) {
    state.detailMode = button.dataset.deckMode;
    await renderView();
  } else if (button.dataset.matchupRow) {
    toggleSet(state.matchupRows, button.dataset.matchupRow);
    await renderView();
  } else if (button.dataset.matchupColumn) {
    toggleSet(state.matchupColumns, button.dataset.matchupColumn);
    await renderView();
  } else if (button.id === "matchup-expand-all") {
    const document = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    const parents = document
      ? document.parent_order.filter(id => document.hierarchy.parents.find(item => item.id === id)?.expandable)
      : [];
    if (state.matchupRows.size || state.matchupColumns.size) {
      state.matchupRows.clear();
      state.matchupColumns.clear();
    } else {
      parents.forEach(id => {
        state.matchupRows.add(id);
        state.matchupColumns.add(id);
      });
    }
    await renderView();
  } else if (button.dataset.top8Detail) {
    state.top8Detail = state.top8Detail === button.dataset.top8Detail
      ? null
      : button.dataset.top8Detail;
    state.detailMode = "average";
    await renderView();
  } else if (button.hasAttribute("data-close-top8")) {
    state.top8Detail = null;
    await renderView();
  } else if (button.dataset.tabletopView) {
    state.tabletopView = button.dataset.tabletopView;
    state.matchupRows.clear();
    state.matchupColumns.clear();
    await renderView();
  } else if (button.dataset.tabletopScope) {
    state.tabletopScope = button.dataset.tabletopScope;
    state.tabletopDetailIdentity = null;
    await renderView();
  } else if (button.dataset.tabletopToggle) {
    toggleSet(state.tabletopExpanded, button.dataset.tabletopToggle);
    state.tabletopDetailIdentity = null;
    await renderView();
  } else if (button.dataset.tabletopDetail) {
    state.tabletopDetailIdentity = state.tabletopDetailIdentity === button.dataset.tabletopDetail
      ? null
      : button.dataset.tabletopDetail;
    state.detailMode = "average";
    await renderView();
  } else if (button.hasAttribute("data-close-tabletop-detail")) {
    state.tabletopDetailIdentity = null;
    await renderView();
  } else if (button.dataset.tabletopSort) {
    if (state.tabletopSort === button.dataset.tabletopSort) {
      state.tabletopDirection = state.tabletopDirection === "desc" ? "asc" : "desc";
    } else {
      state.tabletopSort = button.dataset.tabletopSort;
      state.tabletopDirection = state.tabletopSort === "name" ? "asc" : "desc";
    }
    await renderView();
  } else if (button.id === "tabletop-expand-all") {
    const parents = currentContext.overview.scopes[state.tabletopScope].archetypes
      .filter(item => activeTabletopSubtypes(item).length >= 2);
    if (state.tabletopExpanded.size) state.tabletopExpanded.clear();
    else parents.forEach(item => state.tabletopExpanded.add(item.archetype_id));
    state.tabletopDetailIdentity = null;
    await renderView();
  } else if (button.dataset.pickupWeek) {
    state.pickupWeekFile = button.dataset.pickupWeek;
    state.pickupOpen.clear();
    await renderView();
  } else if (button.dataset.pickupToggle) {
    toggleSet(state.pickupOpen, button.dataset.pickupToggle);
    await renderView();
  }
});

document.addEventListener("change", async event => {
  if (event.target.id === "top8-week") {
    state.top8WeekFile = event.target.value;
    state.top8Detail = null;
    await renderView();
  } else if (event.target.id === "tabletop-event") {
    state.tabletopEventId = event.target.value;
    state.tabletopSelectedEvents.add(event.target.value);
    state.tabletopDetailIdentity = null;
    await renderView();
  } else if (event.target.dataset.tabletopEventCheck) {
    const id = event.target.dataset.tabletopEventCheck;
    if (event.target.checked) state.tabletopSelectedEvents.add(id);
    else if (state.tabletopSelectedEvents.size > 1) state.tabletopSelectedEvents.delete(id);
    else event.target.checked = true;
  }
});

function setPieReadout(slice, pin = false) {
  const card = slice.closest(".pie-card");
  const readout = card?.querySelector(".pie-readout");
  if (!card || !readout) return;
  if (pin) {
    const alreadyPinned = card.dataset.pinnedPieDetail === slice.dataset.pieDetail;
    card.querySelectorAll(".pie-slice.pinned").forEach(item => item.classList.remove("pinned"));
    if (alreadyPinned) {
      delete card.dataset.pinnedPieDetail;
      readout.textContent = t("chart.help");
      return;
    }
    card.dataset.pinnedPieDetail = slice.dataset.pieDetail;
    slice.classList.add("pinned");
  }
  readout.textContent = slice.dataset.pieDetail;
}

function restorePieReadout(slice) {
  const card = slice.closest(".pie-card");
  const readout = card?.querySelector(".pie-readout");
  if (!card || !readout) return;
  readout.textContent = card.dataset.pinnedPieDetail
    || t("chart.help");
}

document.addEventListener("mouseover", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) {
    slice.classList.add("hovered");
    setPieReadout(slice);
  }
  const link = event.target.closest("[data-card-image]");
  if (!link) return;
  const preview = document.querySelector("#card-preview");
  preview.src = link.dataset.cardImage;
  preview.style.display = "block";
});

document.addEventListener("mousemove", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) {
    slice.classList.add("hovered");
    setPieReadout(slice);
  }
  const preview = document.querySelector("#card-preview");
  if (preview.style.display === "block") {
    preview.style.left = `${Math.min(window.innerWidth - 255, event.clientX + 16)}px`;
    preview.style.top = `${Math.max(8, Math.min(window.innerHeight - 345, event.clientY + 16))}px`;
  }
  const cell = event.target.closest("[data-record]");
  const pop = document.querySelector("#matrix-hover-pop");
  if (cell && pop) {
    pop.textContent = t("matchup.record", { record: cell.dataset.record });
    pop.hidden = false;
    pop.style.left = `${Math.min(window.innerWidth - 190, event.clientX + 12)}px`;
    pop.style.top = `${Math.max(8, event.clientY - 38)}px`;
  }
});

document.addEventListener("mouseout", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) {
    slice.classList.remove("hovered");
    restorePieReadout(slice);
  }
  if (event.target.closest("[data-card-image]")) {
    const preview = document.querySelector("#card-preview");
    preview.style.display = "none";
    preview.removeAttribute("src");
  }
  if (event.target.closest("[data-record]")) {
    const pop = document.querySelector("#matrix-hover-pop");
    if (pop) pop.hidden = true;
  }
});

document.addEventListener("focusin", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) setPieReadout(slice);
  const cell = event.target.closest("[data-record]");
  if (!cell) return;
  const node = document.querySelector("#matrix-record");
  if (node) {
    node.textContent = t("matchup.record", { record: cell.dataset.record });
    node.hidden = false;
  }
});

document.addEventListener("focusout", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) restorePieReadout(slice);
});

document.addEventListener("click", event => {
  const slice = event.target.closest(".pie-slice");
  if (slice) {
    setPieReadout(slice, true);
    return;
  }
  const cell = event.target.closest("[data-record]");
  if (!cell) return;
  const node = document.querySelector("#matrix-record");
  if (node) {
    node.textContent = t("matchup.record", { record: cell.dataset.record });
    node.hidden = false;
  }
});

async function changeLanguage(language) {
  I18n.setLanguage(language);
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = t("site.title");
  const siteTitle = document.querySelector("#site-title");
  if (siteTitle) siteTitle.textContent = t("site.title");
  document.querySelector("#lang-zh").classList.toggle("active", language === "zh");
  document.querySelector("#lang-en").classList.toggle("active", language === "en");
  setMessage("");
  renderNavigation();
  await renderView();
}

document.querySelector("#lang-en").addEventListener("click", async () => {
  await changeLanguage("en");
});

document.querySelector("#lang-zh").addEventListener("click", async () => {
  await changeLanguage("zh");
});

function toggleSet(set, value) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
}

async function initialize() {
  try {
    state.catalog = await Runtime.catalog.fetchJson("stats/catalog.json");
    const initialFormat = state.catalog.formats.find(item => item.id === state.format);
    if (!availableProductIds(state.format).includes(state.product)) {
      state.product = availableProductIds(state.format)[0]
        || initialFormat.default_product_id;
    }
    renderNavigation();
    await renderView();
  } catch (error) {
    document.querySelector("#view").innerHTML = `<p class="error-state"><strong>${t("loading.catalog_error")}</strong><br>${escapeHtml(error.message)}</p>`;
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

initialize();
