"use strict";

const ReviewData = globalThis.P8ReviewData;
const Runtime = globalThis.P8Runtime;
const I18n = globalThis.P8I18n;
const MtgoController = globalThis.P8MtgoController;
const TabletopController = globalThis.P8TabletopController;
const ArchetypeVisuals = globalThis.P8ArchetypeVisuals || Object.freeze({
  manaIdentities: Object.freeze({}),
  representativeCards: Object.freeze({}),
});
const REPRESENTATIVE_CARDS = ArchetypeVisuals.representativeCards;
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
const PRODUCT_SURFACES = {
  "mtgo-statistics": "mtgo",
  "mtgo-matchups": "mtgo",
  "mtgo-top8": "mtgo",
  "tabletop-major-events": "tabletop",
  "weekly-pickup": "mtgo",
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
  tabletopLastSelectedEventId: null,
  tabletopLastScopeByEvent: new Map(),
  tabletopWasMultiEvent: false,
  tabletopScope: "all_constructed",
  tabletopExpanded: new Set(),
  tabletopDetailIdentity: null,
  tabletopSort: "deck_count",
  tabletopDirection: "desc",
  scrollHintsSeen: new Set(),
  renderToken: 0,
  failedRender: null,
  pendingRefresh: null,
  refreshInProgress: false,
  viewCheckedAt: new Map(),
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

function navigateToProductEntry(productId, formatId) {
  if (ENTRY_SURFACE === "review") return false;
  const targetSurface = PRODUCT_SURFACES[productId];
  if (!targetSurface || targetSurface === ENTRY_SURFACE) return false;
  const attribute = targetSurface === "tabletop"
    ? "tabletopEntry"
    : "mtgoEntry";
  const entry = document.documentElement.dataset[attribute];
  if (!entry) throw new Error(`Missing ${targetSurface} entry path`);
  const target = new URL(entry, window.location.href);
  target.searchParams.set("format", formatId);
  target.searchParams.set("product", productId);
  target.searchParams.set("lang", I18n.language());
  window.location.assign(target.href);
  return true;
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
    ?.products.filter(item => item.available)
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

function accessibleCompositionSegment({ className, style, label, identity = null, expanded = false }) {
  const safeClass = escapeHtml(className);
  const safeStyle = escapeHtml(style);
  const safeLabel = escapeHtml(label);
  if (identity) {
    return `<button class="${safeClass}" type="button" style="${safeStyle}"
      data-composition-identity="${escapeHtml(identity)}" data-tooltip="${safeLabel}"
      aria-label="${safeLabel}" aria-expanded="${expanded}"><span class="sr-only">${safeLabel}</span></button>`;
  }
  return `<span class="${safeClass}" style="${safeStyle}" tabindex="0" role="img"
    data-tooltip="${safeLabel}" aria-label="${safeLabel}"></span>`;
}

function renderNavigation() {
  const formatRoot = document.querySelector("#format-tabs");
  const productRoot = document.querySelector("#product-tabs");
  const focusedFormat = document.activeElement?.dataset.format;
  const focusedProduct = document.activeElement?.dataset.product;
  const unavailableDescription = document.querySelector("#unavailable-navigation-description");
  if (unavailableDescription) unavailableDescription.textContent = t("availability.developing");
  formatRoot.innerHTML = state.catalog.formats.map(format => {
    const available = format.products.some(item => item.available);
    const describedBy = available ? "" : ' aria-describedby="unavailable-navigation-description"';
    return `<button type="button" data-format="${escapeHtml(format.id)}"
      class="${state.format === format.id ? "active" : ""} ${available ? "" : "unavailable"}"
      aria-pressed="${state.format === format.id}" aria-disabled="${!available}"${describedBy}
      title="${available ? "" : t("availability.developing")}">${formatLabel(format.id, escapeHtml(format.display_name))}</button>`;
  }).join("");
  productRoot.innerHTML = PRODUCT_ORDER.map(productId => {
    const available = Boolean(productEntry(productId)?.available);
    const describedBy = available ? "" : ' aria-describedby="unavailable-navigation-description"';
    return `<button type="button" data-product="${productId}"
      class="${state.product === productId ? "active" : ""} ${available ? "" : "unavailable"}"
      aria-pressed="${state.product === productId}" aria-disabled="${!available}"${describedBy}
      title="${available ? "" : t("availability.developing")}">${productLabel(productId)}</button>`;
  }).join("");
  const focusTarget = focusedFormat
    ? formatRoot.querySelector(`[data-format="${CSS.escape(focusedFormat)}"]`)
    : productRoot.querySelector(`[data-product="${CSS.escape(focusedProduct || "")}"]`);
  focusTarget?.focus({ preventScroll: true });
}

function cardLink(card) {
  const name = card.name;
  const quantity = card.qty ?? card.mean_qty ?? "";
  const search = `https://scryfall.com/search?q=${encodeURIComponent(`!"${name}"`)}`;
  const image = `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=image&version=normal`;
  const rate = card.rate === undefined ? "" : ` <small>(${pct(card.rate)})</small>`;
  return `<li><span class="qty">${escapeHtml(quantity)}</span><a class="card-link"
    href="${search}" target="_blank" rel="noopener"
    data-card-image="${escapeHtml(image)}" data-card-name="${escapeHtml(name)}"
    data-scryfall-url="${escapeHtml(search)}">${escapeHtml(name)}</a>${rate}</li>`;
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
  className = "deck-detail",
  responsiveKey = "",
}) {
  const deck = exactDeck || bestDeck;
  const deckTitle = exactDeck ? exactDeckTitle : t("deck.best");
  const baseStatus = comparison?.base_status;
  const deviation = deck?.deviation;
  const diff = deck?.deviation_diff;
  const responsiveAttribute = suffix => responsiveKey
    ? ` data-responsive-key="${escapeHtml(`${responsiveKey}:${suffix}`)}"`
    : "";
  return `<section class="${className}">
    <button class="deck-close" type="button" ${closeAction}${responsiveAttribute("close")} aria-label="${t("deck.close")}">✕</button>
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
          <button type="button" data-deck-mode="average"${responsiveAttribute("mode-average")} class="${state.detailMode === "average" ? "active" : ""}">${t("deck.average")}</button>
          <button type="button" data-deck-mode="typical"${responsiveAttribute("mode-typical")} class="${state.detailMode === "typical" ? "active" : ""}">${t("deck.representative")}</button>
          <span>（${t("deck.sample", { count: averageDeck?.sample_size ?? "—" })}）</span>
        </div>
        ${averageDeckHtml(averageDeck)}
      </div>
    </div>
  </section>`;
}
