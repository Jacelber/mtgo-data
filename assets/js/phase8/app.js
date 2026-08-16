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
let touchedCompositionIdentity = null;

function clearTouchedComposition() {
  document.querySelectorAll(".composition-segment.touch-active")
    .forEach(segment => segment.classList.remove("touch-active"));
  touchedCompositionIdentity = null;
}

function setCompositionSelection(parentId) {
  state.compositionIdentity = parentId || null;
  document.querySelectorAll("button[data-composition-identity]").forEach(button => {
    const selected = button.dataset.compositionIdentity === state.compositionIdentity;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-expanded", String(selected));
  });
}

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
      state.compositionIdentity = detail.split("/", 1)[0];
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

function currentDetailReveal() {
  const mobile = matchMedia("(max-width: 780px)").matches;
  if (state.product === "mtgo-statistics" && state.detailIdentity) {
    return {
      selector: mobile
        ? `[data-mobile-expanded-content="stats:${CSS.escape(state.detailIdentity)}"]`
        : ".deck-detail-row",
      alignment: mobile ? "start" : "end",
    };
  }
  if (
    state.product === "tabletop-major-events"
    && state.tabletopView === "overview"
    && state.tabletopDetailIdentity
  ) {
    return {
      selector: mobile
        ? `[data-mobile-expanded-content="tabletop:${CSS.escape(state.tabletopDetailIdentity)}"]`
        : ".deck-detail-row",
      alignment: mobile ? "start" : "end",
    };
  }
  return { selector: null, alignment: "end" };
}

async function renderView() {
  return renderViewWithFocus();
}

async function renderViewWithFocus(
  focusOverride = null,
  revealSelector = null,
  { focusTitle = false, revealAlignment = "end" } = {}
) {
  const root = document.querySelector("#view");
  clearTouchedComposition();
  const focusSelector = focusOverride || renderFocusSelector(document.activeElement, root);
  const position = captureRenderPosition(root, focusSelector);
  const preserveExistingContent = root.childElementCount > 0
    && !root.querySelector(".loading-state, .error-state");
  const token = ++state.renderToken;
  root.querySelectorAll(".inline-error-state, .load-error-row").forEach(node => node.remove());
  root.setAttribute("aria-busy", "true");
  root.inert = true;
  if (preserveExistingContent) {
    root.style.minHeight = `${Math.ceil(root.getBoundingClientRect().height)}px`;
  } else {
    root.innerHTML = loadingSkeleton();
  }
  try {
    let html;
    if (state.product === "mtgo-statistics") html = await statsView();
    else if (state.product === "mtgo-matchups") html = await matchupView();
    else if (state.product === "mtgo-top8") html = await top8View();
    else if (state.product === "tabletop-major-events") html = await tabletopView();
    else html = await pickupView();
    if (token !== state.renderToken) return;
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    root.inert = false;
    state.failedRender = null;
    if (!state.viewCheckedAt.has(currentViewKey())) {
      state.viewCheckedAt.set(currentViewKey(), Date.now());
    }
    updateFreshnessLayouts(root);
    globalThis.P8CardImages?.observe(root);
    restoreRenderPosition(root, focusSelector, position);
    updateMatrixStickyHeader();
    requestAnimationFrame(() => {
      updateFreshnessLayouts(root);
      restoreRenderPosition(root, focusSelector, position);
      root.style.removeProperty("min-height");
      requestAnimationFrame(() => {
        restoreRenderPosition(root, focusSelector, position);
        if (focusTitle) focusViewTitle(root);
        else restoreRenderFocus(root, focusSelector);
        revealExpandedContent(root, revealSelector, revealAlignment);
        updateMatrixPresentation();
      });
    });
    document.querySelector("#payload-status").textContent = t("loading.loaded", {
      format: formatLabel(state.format),
      product: productLabel(state.product),
    });
  } catch (error) {
    if (token !== state.renderToken) return;
    state.failedRender = {
      error,
      focusSelector,
      preserveExistingContent,
      revealSelector,
    };
    if (preserveExistingContent) {
      placeScopedError(root, focusSelector);
    } else {
      root.innerHTML = `<section class="error-state" role="alert">${retryMarkup()}</section>`;
      root.querySelector("button")?.focus({ preventScroll: true });
    }
    root.removeAttribute("aria-busy");
    root.inert = false;
    root.style.removeProperty("min-height");
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
  flushUrlWrite();
}

function resetInteractions() {
  clearTouchedComposition();
  setCompositionSelection(null);
  state.statsExpanded.clear();
  state.matchupRows.clear();
  state.matchupColumns.clear();
  state.matchupFilterIdentities = null;
  state.matchupFilterDraft.clear();
  state.matchupFilterExpanded.clear();
  state.matchupFilterOpen = false;
  state.tabletopExpanded.clear();
  state.detailIdentity = null;
  state.top8Detail = null;
  state.tabletopDetailIdentity = null;
  state.scrollHintsSeen.clear();
}

document.addEventListener("click", async event => {
  const compositionButton = event.target.closest("button[data-composition-identity]");
  if (!compositionButton) clearTouchedComposition();
  const button = event.target.closest("button");
  if (!button) return;
  if (button.hasAttribute("data-retry-view")) {
    const failed = state.failedRender;
    button.disabled = true;
    button.textContent = t("loading.retrying");
    await renderViewWithFocus(
      failed?.focusSelector || null,
      failed?.revealSelector || null,
      { focusTitle: !failed?.preserveExistingContent }
    );
    return;
  }
  if (button.hasAttribute("data-retry-catalog")) {
    button.disabled = true;
    button.textContent = t("loading.retrying");
    await initialize({ retry: true });
    return;
  }
  if (button.hasAttribute("data-retry-refresh")) {
    button.disabled = true;
    button.textContent = t("loading.retrying");
    await checkForUpdates();
    return;
  }
  if (button.hasAttribute("data-apply-refresh")) {
    commitPendingRefresh();
    await renderViewWithFocus(null, null, { focusTitle: true });
    return;
  }
  if (await handleMobileListClick(button)) return;
  if (button.dataset.format) {
    discardPendingRefresh();
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
    discardPendingRefresh();
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
  } else if (button.dataset.compositionIdentity) {
    const parentId = button.dataset.compositionIdentity;
    const touchContract = matchMedia("(hover: none)").matches || matchMedia("(max-width: 780px)").matches;
    if (touchContract && touchedCompositionIdentity !== parentId) {
      clearTouchedComposition();
      button.classList.add("touch-active");
      touchedCompositionIdentity = parentId;
      return;
    }
    clearTouchedComposition();
    const action = currentCompositionAction(parentId);
    setCompositionSelection(parentId);
    if (action.kind === "subtypes") {
      state.statsExpanded.add(action.parentId);
      if (state.detailIdentity) queueUrlWrite();
      state.detailIdentity = null;
      const revealSelector = matchMedia("(max-width: 780px)").matches
        ? `[data-mobile-card-identity="${CSS.escape(action.parentId)}"]`
        : `[data-stats-subtype-end="${CSS.escape(action.parentId)}"]`;
      await renderViewWithFocus(null, revealSelector, {
        revealAlignment: matchMedia("(max-width: 780px)").matches ? "start" : "end",
      });
      return;
    }
    state.detailIdentity = action.identity;
    state.detailMode = "average";
    queueUrlWrite();
    const revealSelector = matchMedia("(max-width: 780px)").matches
      ? `[data-mobile-card-identity="${CSS.escape(action.identity)}"]`
      : ".deck-detail-row";
    await renderViewWithFocus(null, revealSelector, {
      revealAlignment: matchMedia("(max-width: 780px)").matches ? "start" : "end",
    });
  } else if (button.dataset.statsRange) {
    discardPendingRefresh();
    state.statsRange = Number(button.dataset.statsRange);
    state.detailIdentity = null;
    setCompositionSelection(null);
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.matchupRange) {
    discardPendingRefresh();
    state.matchupRange = Number(button.dataset.matchupRange);
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.statsToggle) {
    const parentId = button.dataset.statsToggle;
    const opening = !state.statsExpanded.has(parentId);
    toggleSet(state.statsExpanded, parentId);
    if (opening) setCompositionSelection(parentId);
    else if (state.compositionIdentity === parentId) setCompositionSelection(null);
    if (state.detailIdentity) queueUrlWrite();
    state.detailIdentity = null;
    if (!renderStatsExpansion(button)) await renderView();
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
    setCompositionSelection(null);
    if (state.detailIdentity) queueUrlWrite();
    state.detailIdentity = null;
    if (!renderStatsExpansion(button)) await renderView();
  } else if (button.dataset.detailIdentity) {
    const identity = button.dataset.detailIdentity;
    const opening = state.detailIdentity !== identity;
    state.detailIdentity = opening ? identity : null;
    const parentId = identity.split("/", 1)[0];
    if (opening) setCompositionSelection(parentId);
    else if (state.compositionIdentity === parentId) setCompositionSelection(null);
    state.detailMode = "average";
    queueUrlWrite();
    await renderView();
  } else if (button.hasAttribute("data-close-detail")) {
    const identity = state.detailIdentity;
    state.detailIdentity = null;
    if (state.compositionIdentity === identity?.split("/", 1)[0]) {
      setCompositionSelection(null);
    }
    queueUrlWrite();
    await renderViewWithFocus(`[data-detail-identity="${CSS.escape(identity || "")}"]`);
  } else if (button.dataset.deckMode) {
    state.detailMode = button.dataset.deckMode;
    await renderView();
  } else if (button.hasAttribute("data-matchup-mainstream-retry")) {
    await renderViewWithFocus("[data-matchup-mainstream]");
  } else if (button.hasAttribute("data-matchup-filter-toggle")) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (matchupDocument) setMatchupFilterMenuOpen(!state.matchupFilterOpen, matchupDocument);
  } else if (button.dataset.matchupFilterParent) {
    const parentId = button.dataset.matchupFilterParent;
    toggleSet(state.matchupFilterExpanded, parentId);
    const expanded = state.matchupFilterExpanded.has(parentId);
    button.setAttribute("aria-expanded", String(expanded));
    button.querySelector("span").textContent = expanded ? "−" : "+";
    const childList = document.querySelector(`#matchup-filter-children-${CSS.escape(parentId)}`);
    if (childList) childList.hidden = !expanded;
  } else if (button.hasAttribute("data-matchup-filter-apply")) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (!matchupDocument || !state.matchupFilterDraft.size) return;
    const allIds = matchupFilterCandidateIds(matchupDocument);
    state.matchupFilterIdentities = state.matchupFilterDraft.size === allIds.length
      ? null
      : new Set(state.matchupFilterDraft);
    if (state.matchupFilterIdentities === null) state.matchupRows.clear();
    state.matchupFilterOpen = false;
    await renderViewWithFocus("[data-matchup-filter-toggle]");
  } else if (button.hasAttribute("data-matchup-filter-cancel")) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (matchupDocument) setMatchupFilterMenuOpen(false, matchupDocument);
  } else if (button.hasAttribute("data-matchup-filter-reset")) {
    state.matchupFilterIdentities = null;
    state.matchupRows.clear();
    state.matchupFilterOpen = false;
    await renderViewWithFocus("[data-matchup-filter-toggle]");
  } else if (button.dataset.matchupRow) {
    const parentId = button.dataset.matchupRow;
    toggleSet(state.matchupRows, parentId);
    await renderView();
  } else if (button.dataset.matchupColumn) {
    const parentId = button.dataset.matchupColumn;
    toggleSet(state.matchupColumns, parentId);
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
    const detail = state.top8Detail;
    state.top8Detail = null;
    queueUrlWrite();
    await renderViewWithFocus(`[data-top8-detail="${CSS.escape(detail || "")}"]`);
  } else if (button.dataset.tabletopView) {
    discardPendingRefresh();
    state.tabletopView = button.dataset.tabletopView;
    state.scrollHintsSeen.clear();
    if (state.tabletopView === "overview" && state.tabletopLastSelectedEventId) {
      state.tabletopEventId = state.tabletopLastSelectedEventId;
    }
    state.matchupRows.clear();
    state.matchupColumns.clear();
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.tabletopScope) {
    discardPendingRefresh();
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
    const identity = state.tabletopDetailIdentity;
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
    await renderViewWithFocus(`[data-tabletop-detail="${CSS.escape(identity || "")}"]`);
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
    discardPendingRefresh();
    state.pickupWeekFile = button.dataset.pickupWeek;
    state.pickupOpen.clear();
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.pickupToggle) {
    toggleSet(state.pickupOpen, button.dataset.pickupToggle);
    await renderView();
  }
});

document.addEventListener("input", event => {
  if (event.target.id === "matchup-filter-search") {
    updateMatchupFilterCandidateVisibility(event.target.value);
  }
});

document.addEventListener("change", async event => {
  if (await handleMobileListChange(event.target)) return;
  if (event.target.hasAttribute("data-matchup-mainstream")) {
    state.matchupMainstreamOnly = event.target.checked;
    state.matchupFilterOpen = false;
    await renderViewWithFocus("[data-matchup-mainstream]");
  } else if (event.target.hasAttribute("data-matchup-filter-select-all")) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (!matchupDocument) return;
    state.matchupFilterDraft = event.target.checked
      ? new Set(matchupFilterCandidateIds(matchupDocument))
      : new Set();
    document.querySelectorAll("[data-matchup-filter-option]").forEach(option => {
      option.checked = event.target.checked;
    });
    updateMatchupFilterDraftControls(matchupDocument);
  } else if (event.target.dataset.matchupFilterOption) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (!matchupDocument) return;
    if (event.target.checked) state.matchupFilterDraft.add(event.target.dataset.matchupFilterOption);
    else state.matchupFilterDraft.delete(event.target.dataset.matchupFilterOption);
    updateMatchupFilterDraftControls(matchupDocument);
  } else if (event.target.id === "top8-week") {
    discardPendingRefresh();
    state.top8WeekFile = event.target.value;
    state.top8Detail = null;
    queueUrlWrite();
    await renderView();
  } else if (event.target.id === "tabletop-event") {
    discardPendingRefresh();
    state.tabletopEventId = event.target.value;
    state.tabletopLastSelectedEventId = event.target.value;
    state.tabletopSelectedEvents = new Set([event.target.value]);
    state.tabletopWasMultiEvent = false;
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
    await renderView();
  } else if (event.target.dataset.tabletopEventCheck) {
    discardPendingRefresh();
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

document.addEventListener("mousemove", event => {
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
  if (event.target.closest("[data-record]")) {
    const pop = document.querySelector("#matrix-hover-pop");
    if (pop) pop.hidden = true;
  }
});

document.addEventListener("focusin", event => {
  const cell = event.target.closest("[data-record]");
  if (!cell) return;
  const node = document.querySelector("#matrix-record");
  if (node) {
    node.textContent = t("matchup.record", { record: cell.dataset.record });
    node.hidden = false;
  }
});

document.addEventListener("click", event => {
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
  discardPendingRefresh();
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

async function initialize({ retry = false } = {}) {
  const view = document.querySelector("#view");
  if (retry) {
    view.setAttribute("aria-busy", "true");
    view.innerHTML = loadingSkeleton();
  }
  try {
    state.catalog = await Runtime.catalog.fetchJson("stats/catalog.json");
    const parameters = new URLSearchParams(window.location.search);
    resetUrlBackedState();
    applyUrlState(parameters);
    if (navigateToProductEntry(state.product, state.format)) return;
    if (hasExtendedUrlState(parameters)) queueUrlWrite("replace");
    renderNavigation();
    const reveal = currentDetailReveal();
    await renderViewWithFocus(null, reveal.selector, {
      revealAlignment: reveal.alignment,
    });
  } catch (error) {
    state.failedRender = { error, preserveExistingContent: false };
    view.removeAttribute("aria-busy");
    view.innerHTML = `<section class="error-state" role="alert">
      <strong>${t("loading.catalog_error")}</strong>
      <p class="resource-error-message">${resourceErrorMessage(error)}</p>
      <button class="secondary-button" type="button" data-retry-catalog>${t("loading.catalog_retry")}</button>
    </section>`;
    view.querySelector("button")?.focus({ preventScroll: true });
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

window.addEventListener("popstate", async () => {
  if (!state.catalog) return;
  discardPendingRefresh();
  resetUrlBackedState();
  applyUrlState(new URLSearchParams(window.location.search));
  if (navigateToProductEntry(state.product, state.format)) return;
  setMessage("");
  renderNavigation();
  const reveal = currentDetailReveal();
  await renderViewWithFocus(null, reveal.selector, {
    revealAlignment: reveal.alignment,
  });
});

initialize();
