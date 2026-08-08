"use strict";

const STATS_SORT_KEYS = new Set([
  "name",
  "avg_points_per_round",
  "high_score_count",
  "high_score_share",
  "top8_count",
  "top8_share",
  "conversion",
]);
const TABLETOP_SORT_KEYS = new Set([
  "name",
  "deck_count",
  "metagame_share",
  "average_points_per_effective_round",
  "win_rate",
  "matches",
  "completion_rate",
  "day2_conversion",
  "high_score",
]);
const TABLETOP_VIEWS = new Set(["overview", "matchup"]);
const TABLETOP_SCOPES = new Set(["day1", "day2", "all_constructed"]);
const EXTENDED_URL_KEYS = [
  "range", "sort", "dir", "week", "event", "events", "view", "scope", "detail",
];
let pendingUrlWrite = null;

function resetUrlBackedState() {
  state.format = "modern";
  state.product = "mtgo-statistics";
  state.statsRange = 1;
  state.matchupRange = 4;
  state.statsSort = "high_score_share";
  state.statsDirection = "desc";
  state.detailMode = "average";
  state.top8WeekFile = null;
  state.pickupWeekFile = null;
  state.pickupOpen.clear();
  state.tabletopView = "overview";
  state.tabletopEventId = null;
  state.tabletopSelectedEvents.clear();
  state.tabletopLastSelectedEventId = null;
  state.tabletopLastScopeByEvent.clear();
  state.tabletopWasMultiEvent = false;
  state.tabletopScope = "all_constructed";
  state.tabletopSort = "deck_count";
  state.tabletopDirection = "desc";
  pendingUrlWrite = null;
  resetInteractions();
}

function requestedWeekFile(parameters) {
  const week = parameters.get("week");
  return /^\d{4}-W\d{2}$/.test(week || "") ? `${week}.json` : null;
}

function applyUrlState(parameters) {
  const language = parameters.get("lang");
  updateLanguageChrome(language === "en" ? "en" : "zh");

  const requestedFormat = parameters.get("format");
  if (
    requestedFormat
    && state.catalog.formats.some(item => (
      item.id === requestedFormat && availableProductIds(item.id).length
    ))
  ) {
    state.format = requestedFormat;
  }
  const initialFormat = state.catalog.formats.find(item => item.id === state.format);
  const requestedProduct = parameters.get("product");
  const preferredProduct = requestedProduct
    || (ENTRY_SURFACE === "tabletop" ? "tabletop-major-events" : state.product);
  if (availableProductIds(state.format).includes(preferredProduct)) {
    state.product = preferredProduct;
  } else {
    state.product = availableProductIds(state.format)[0]
      || initialFormat.default_product_id;
  }

  const range = Number(parameters.get("range"));
  const sort = parameters.get("sort");
  const direction = parameters.get("dir");
  const detail = parameters.get("detail");
  if (state.product === "mtgo-statistics") {
    if (RANGE_OPTIONS.includes(range)) state.statsRange = range;
    if (STATS_SORT_KEYS.has(sort)) state.statsSort = sort;
    if (direction === "asc" || direction === "desc") state.statsDirection = direction;
    if (detail) {
      state.detailIdentity = detail;
      if (detail.includes("/")) state.statsExpanded.add(detail.split("/", 1)[0]);
    }
  } else if (state.product === "mtgo-matchups") {
    if (RANGE_OPTIONS.includes(range)) state.matchupRange = range;
  } else if (state.product === "mtgo-top8") {
    state.top8WeekFile = requestedWeekFile(parameters);
    if (detail) state.top8Detail = detail;
  } else if (state.product === "weekly-pickup") {
    state.pickupWeekFile = requestedWeekFile(parameters);
  } else if (state.product === "tabletop-major-events") {
    const view = parameters.get("view");
    const eventId = parameters.get("event");
    const scope = parameters.get("scope");
    if (TABLETOP_VIEWS.has(view)) state.tabletopView = view;
    if (eventId) {
      state.tabletopEventId = eventId;
      state.tabletopSelectedEvents.add(eventId);
      state.tabletopLastSelectedEventId = eventId;
    }
    if (TABLETOP_SCOPES.has(scope)) state.tabletopScope = scope;
    if (TABLETOP_SORT_KEYS.has(sort)) state.tabletopSort = sort;
    if (direction === "asc" || direction === "desc") state.tabletopDirection = direction;
    if (state.tabletopView === "overview" && detail) {
      state.tabletopDetailIdentity = detail;
      if (detail.includes("/")) state.tabletopExpanded.add(detail.split("/", 1)[0]);
    }
  }
}

function weekId(file) {
  return file?.endsWith(".json") ? file.slice(0, -5) : null;
}

function urlStateParameters() {
  const parameters = new URLSearchParams();
  parameters.set("format", state.format);
  parameters.set("product", state.product);
  if (state.product === "mtgo-statistics") {
    parameters.set("range", String(state.statsRange));
    parameters.set("sort", state.statsSort);
    parameters.set("dir", state.statsDirection);
    if (state.detailIdentity) parameters.set("detail", state.detailIdentity);
  } else if (state.product === "mtgo-matchups") {
    parameters.set("range", String(state.matchupRange));
  } else if (state.product === "mtgo-top8") {
    if (weekId(state.top8WeekFile)) parameters.set("week", weekId(state.top8WeekFile));
    if (state.top8Detail) parameters.set("detail", state.top8Detail);
  } else if (state.product === "weekly-pickup") {
    if (weekId(state.pickupWeekFile)) parameters.set("week", weekId(state.pickupWeekFile));
  } else if (state.product === "tabletop-major-events") {
    parameters.set("view", state.tabletopView);
    if (state.tabletopEventId) parameters.set("event", state.tabletopEventId);
    parameters.set("scope", state.tabletopScope);
    if (state.tabletopView === "overview") {
      parameters.set("sort", state.tabletopSort);
      parameters.set("dir", state.tabletopDirection);
      if (state.tabletopDetailIdentity) {
        parameters.set("detail", state.tabletopDetailIdentity);
      }
    }
  }
  // Phase 13 owns `events=<sorted,unique,event,ids>`; P12-02 reserves but omits it.
  parameters.set("lang", I18n.language());
  return parameters;
}

function queueUrlWrite(mode = "push") {
  pendingUrlWrite = mode;
}

function flushUrlWrite() {
  if (!pendingUrlWrite) return;
  const mode = pendingUrlWrite;
  pendingUrlWrite = null;
  const target = new URL(window.location.href);
  target.search = urlStateParameters().toString();
  const next = `${target.pathname}${target.search}${target.hash}`;
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (next !== current) window.history[`${mode}State`]({}, "", next);
}

function hasExtendedUrlState(parameters) {
  return EXTENDED_URL_KEYS.some(key => parameters.has(key));
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
  flushUrlWrite();
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
    if (navigateToProductEntry(state.product, state.format)) return;
    resetInteractions();
    setMessage("");
    renderNavigation();
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.product) {
    if (!productEntry(button.dataset.product)?.available) {
      setMessage(t("availability.product", {
        format: formatLabel(state.format),
        product: productLabel(button.dataset.product),
      }));
      return;
    }
    state.product = button.dataset.product;
    if (navigateToProductEntry(state.product, state.format)) return;
    resetInteractions();
    setMessage("");
    renderNavigation();
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.statsRange) {
    state.statsRange = Number(button.dataset.statsRange);
    state.detailIdentity = null;
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.matchupRange) {
    state.matchupRange = Number(button.dataset.matchupRange);
    queueUrlWrite();
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
    queueUrlWrite();
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
    queueUrlWrite();
    await renderView();
  } else if (button.hasAttribute("data-close-detail")) {
    state.detailIdentity = null;
    queueUrlWrite();
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
    queueUrlWrite();
    await renderView();
  } else if (button.hasAttribute("data-close-top8")) {
    state.top8Detail = null;
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.tabletopView) {
    state.tabletopView = button.dataset.tabletopView;
    if (state.tabletopView === "overview" && state.tabletopLastSelectedEventId) {
      state.tabletopEventId = state.tabletopLastSelectedEventId;
    }
    state.matchupRows.clear();
    state.matchupColumns.clear();
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.tabletopScope) {
    state.tabletopScope = button.dataset.tabletopScope;
    state.tabletopLastScopeByEvent.set(
      state.tabletopEventId,
      state.tabletopScope
    );
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
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
    queueUrlWrite();
    await renderView();
  } else if (button.hasAttribute("data-close-tabletop-detail")) {
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.tabletopSort) {
    if (state.tabletopSort === button.dataset.tabletopSort) {
      state.tabletopDirection = state.tabletopDirection === "desc" ? "asc" : "desc";
    } else {
      state.tabletopSort = button.dataset.tabletopSort;
      state.tabletopDirection = state.tabletopSort === "name" ? "asc" : "desc";
    }
    queueUrlWrite();
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
    queueUrlWrite();
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
    queueUrlWrite();
    await renderView();
  } else if (event.target.id === "tabletop-event") {
    state.tabletopEventId = event.target.value;
    state.tabletopLastSelectedEventId = event.target.value;
    state.tabletopSelectedEvents = new Set([event.target.value]);
    state.tabletopWasMultiEvent = false;
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
    await renderView();
  } else if (event.target.dataset.tabletopEventCheck) {
    const id = event.target.dataset.tabletopEventCheck;
    if (event.target.checked) {
      state.tabletopSelectedEvents.add(id);
      state.tabletopEventId = id;
      state.tabletopLastSelectedEventId = id;
    } else if (state.tabletopSelectedEvents.size > 1) {
      state.tabletopSelectedEvents.delete(id);
      if (state.tabletopEventId === id) {
        state.tabletopEventId = [...state.tabletopSelectedEvents].at(-1);
      }
      state.tabletopLastSelectedEventId = state.tabletopEventId;
    } else {
      event.target.checked = true;
      return;
    }
    state.tabletopDetailIdentity = null;
    state.matchupRows.clear();
    state.matchupColumns.clear();
    await renderView();
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

function updateLanguageChrome(language) {
  I18n.setLanguage(language);
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = t("site.title");
  const siteTitle = document.querySelector("#site-title");
  if (siteTitle) siteTitle.textContent = t("site.title");
  const zhButton = document.querySelector("#lang-zh");
  const enButton = document.querySelector("#lang-en");
  zhButton.classList.toggle("active", language === "zh");
  enButton.classList.toggle("active", language === "en");
  zhButton.setAttribute("aria-pressed", String(language === "zh"));
  enButton.setAttribute("aria-pressed", String(language === "en"));
}

async function changeLanguage(language) {
  updateLanguageChrome(language);
  setMessage("");
  renderNavigation();
  queueUrlWrite();
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
    const parameters = new URLSearchParams(window.location.search);
    resetUrlBackedState();
    applyUrlState(parameters);
    if (navigateToProductEntry(state.product, state.format)) return;
    if (hasExtendedUrlState(parameters)) queueUrlWrite("replace");
    renderNavigation();
    await renderView();
  } catch (error) {
    document.querySelector("#view").innerHTML = `<p class="error-state"><strong>${t("loading.catalog_error")}</strong><br>${escapeHtml(error.message)}</p>`;
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

window.addEventListener("popstate", async () => {
  if (!state.catalog) return;
  resetUrlBackedState();
  applyUrlState(new URLSearchParams(window.location.search));
  if (navigateToProductEntry(state.product, state.format)) return;
  setMessage("");
  renderNavigation();
  await renderView();
});

initialize();
