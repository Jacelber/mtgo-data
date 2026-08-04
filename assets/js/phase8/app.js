"use strict";

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
    if (navigateToProductEntry(state.product, state.format)) return;
    resetInteractions();
    setMessage("");
    renderNavigation();
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
    if (state.tabletopView === "overview" && state.tabletopLastSelectedEventId) {
      state.tabletopEventId = state.tabletopLastSelectedEventId;
    }
    state.matchupRows.clear();
    state.matchupColumns.clear();
    await renderView();
  } else if (button.dataset.tabletopScope) {
    state.tabletopScope = button.dataset.tabletopScope;
    state.tabletopLastScopeByEvent.set(
      state.tabletopEventId,
      state.tabletopScope
    );
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
    state.tabletopLastSelectedEventId = event.target.value;
    state.tabletopSelectedEvents = new Set([event.target.value]);
    state.tabletopWasMultiEvent = false;
    state.tabletopDetailIdentity = null;
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
  document.querySelector("#lang-zh").classList.toggle("active", language === "zh");
  document.querySelector("#lang-en").classList.toggle("active", language === "en");
}

async function changeLanguage(language) {
  updateLanguageChrome(language);
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
    const parameters = new URLSearchParams(window.location.search);
    const requestedLanguage = parameters.get("lang");
    if (requestedLanguage === "zh" || requestedLanguage === "en") {
      updateLanguageChrome(requestedLanguage);
    }
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
    if (navigateToProductEntry(state.product, state.format)) return;
    renderNavigation();
    await renderView();
  } catch (error) {
    document.querySelector("#view").innerHTML = `<p class="error-state"><strong>${t("loading.catalog_error")}</strong><br>${escapeHtml(error.message)}</p>`;
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

initialize();
