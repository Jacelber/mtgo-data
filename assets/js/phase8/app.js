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
  "range", "sort", "dir", "week", "event", "events", "view", "scope", "detail", "section", "feature", "mode", "mainstream", "filter", "rows", "cols", "expanded",
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
  state.product = state.catalog?.formats
    .find(item => item.id === state.format)?.default_product_id || "mtgo-statistics";
  state.statsRange = 1;
  state.matchupRange = 4;
  state.statsSort = "high_score_share";
  state.statsDirection = "desc";
  state.detailMode = "average";
  state.matchupMainstreamOnly = false;
  state.top8WeekFile = null;
  state.landingFeatureWeekFile = null;
  state.landingFeatureDestination = null;
  state.landingSection = null;
  state.landingFeatureOpen.clear();
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

function routeIdentities(parameters, key) {
  const raw = parameters.get(key);
  if (!raw || raw.length > 20000) return new Set();
  const ids = raw.split(",");
  const valid = /^[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)?$/;
  return ids.length <= 500 && ids.every(id => valid.test(id)) ? new Set(ids) : new Set();
}

function isMatchupView() {
  return state.product === "mtgo-matchups"
    || (state.product === "tabletop-major-events" && state.tabletopView === "matchup");
}

function applyUrlState(parameters) {
  const language = P8Metadata.resolveLanguage(parameters.get("lang"), window.localStorage);
  updateLanguageChrome(language);

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
  if (state.product === "mtgo-landing") {
    state.landingFeatureWeekFile = requestedWeekFile(parameters);
    state.landingSection = parameters.get("section") === "features" ? "features" : null;
    const feature = parameters.get("feature");
    if (/^deck:[0-9a-f]{20}$/.test(feature || "")) {
      state.landingFeatureDestination = feature;
      state.landingSection = "features";
    }
    if (detail) {
      state.detailIdentity = detail;
      state.compositionIdentity = detail;
    }
  } else if (state.product === "mtgo-statistics") {
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
  } else if (state.product === "tabletop-major-events") {
    const view = parameters.get("view");
    const eventId = parameters.get("event");
    const rawEventIds = parameters.get("events");
    const scope = parameters.get("scope");
    if (TABLETOP_VIEWS.has(view)) state.tabletopView = view;
    if (eventId) {
      state.tabletopEventId = eventId;
      state.tabletopLastSelectedEventId = eventId;
    }
    const selectedEventIds = state.tabletopView === "matchup"
      ? TabletopController.parseSelectedEventIds(rawEventIds)
      : null;
    if (selectedEventIds) {
      state.tabletopSelectedEvents = new Set(selectedEventIds);
    } else if (eventId) {
      state.tabletopSelectedEvents.add(eventId);
    }
    if (
      state.tabletopView === "matchup"
      && (selectedEventIds === null || rawEventIds !== selectedEventIds.join(","))
    ) {
      queueUrlWrite("replace");
    }
    if (TABLETOP_SCOPES.has(scope)) state.tabletopScope = scope;
    if (TABLETOP_SORT_KEYS.has(sort)) state.tabletopSort = sort;
    if (direction === "asc" || direction === "desc") state.tabletopDirection = direction;
    if (state.tabletopView === "overview" && detail) {
      state.tabletopDetailIdentity = detail;
      if (detail.includes("/")) state.tabletopExpanded.add(detail.split("/", 1)[0]);
    }
  }
  if (state.detailIdentity || state.top8Detail || state.tabletopDetailIdentity
      || state.landingFeatureDestination) {
    state.detailMode = parameters.get("mode") === "typical" ? "typical" : "average";
  }
  if (state.product === "mtgo-statistics") {
    routeIdentities(parameters, "expanded").forEach(id => state.statsExpanded.add(id));
  } else if (state.product === "tabletop-major-events" && state.tabletopView === "overview") {
    routeIdentities(parameters, "expanded").forEach(id => state.tabletopExpanded.add(id));
  }
  if (isMatchupView()) {
    state.matchupMainstreamOnly = parameters.get("mainstream") === "1";
    const selected = routeIdentities(parameters, "filter");
    state.matchupFilterIdentities = selected.size ? selected : null;
    state.matchupRows = routeIdentities(parameters, "rows");
    state.matchupColumns = routeIdentities(parameters, "cols");
  }

}

function weekId(file) {
  return file?.endsWith(".json") ? file.slice(0, -5) : null;
}

function urlStateParameters() {
  const parameters = new URLSearchParams();
  parameters.set("format", state.format);
  parameters.set("product", state.product);
  if (state.product === "mtgo-landing") {
    if (state.landingSection === "features") parameters.set("section", "features");
    if (weekId(state.landingFeatureWeekFile)) parameters.set("week", weekId(state.landingFeatureWeekFile));
    if (state.landingFeatureDestination) parameters.set("feature", state.landingFeatureDestination);
    if (state.detailIdentity) parameters.set("detail", state.detailIdentity);
  } else if (state.product === "mtgo-statistics") {
    parameters.set("range", String(state.statsRange));
    parameters.set("sort", state.statsSort);
    parameters.set("dir", state.statsDirection);
    if (state.detailIdentity) parameters.set("detail", state.detailIdentity);
  } else if (state.product === "mtgo-matchups") {
    parameters.set("range", String(state.matchupRange));
  } else if (state.product === "mtgo-top8") {
    if (weekId(state.top8WeekFile)) parameters.set("week", weekId(state.top8WeekFile));
    if (state.top8Detail) parameters.set("detail", state.top8Detail);
  } else if (state.product === "tabletop-major-events") {
    parameters.set("view", state.tabletopView);
    if (state.tabletopEventId) parameters.set("event", state.tabletopEventId);
    if (state.tabletopView === "matchup" && state.tabletopSelectedEvents.size) {
      const eventIds = TabletopController.parseSelectedEventIds(
        [...state.tabletopSelectedEvents].join(",")
      );
      if (eventIds) parameters.set("events", eventIds.join(","));
    }
    parameters.set("scope", state.tabletopScope);
    if (state.tabletopView === "overview") {
      parameters.set("sort", state.tabletopSort);
      parameters.set("dir", state.tabletopDirection);
      if (state.tabletopDetailIdentity) {
        parameters.set("detail", state.tabletopDetailIdentity);
      }
    }
  }
  const identities = (key, values) => {
    if (values?.size) parameters.set(key, [...values].sort().join(","));
  };
  if (state.detailMode === "typical" && (state.detailIdentity || state.top8Detail
      || state.tabletopDetailIdentity || state.landingFeatureDestination)) parameters.set("mode", "typical");
  if (state.product === "mtgo-statistics") identities("expanded", state.statsExpanded);
  if (state.product === "tabletop-major-events" && state.tabletopView === "overview") {
    identities("expanded", state.tabletopExpanded);
  }
  if (isMatchupView()) {
    if (state.matchupMainstreamOnly) parameters.set("mainstream", "1");
    identities("filter", state.matchupFilterIdentities);
    identities("rows", state.matchupRows);
    identities("cols", state.matchupColumns);
  }
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
  updateDocumentMetadata();
}

let shareFeedbackTimer = null;
let shareAttempt = 0;

function resetShareFeedback() {
  shareAttempt += 1;
  clearTimeout(shareFeedbackTimer);
  shareFeedbackTimer = null;
  const button = document.querySelector("[data-share-view]");
  button?.classList.remove("is-copied");
  button?.setAttribute("title", t("share.copy"));
  button?.setAttribute("aria-label", t("share.copy"));
  const status = document.querySelector("#share-status");
  if (status) status.textContent = "";
  const input = document.querySelector("#share-link");
  if (input) input.hidden = true;
  const fallback = document.querySelector("#share-fallback");
  if (fallback) fallback.hidden = true;
}

function positionShareFallback() {
  const panel = document.querySelector("#share-fallback");
  const button = document.querySelector("[data-share-view]");
  if (!panel || panel.hidden || !button) return;
  const box = button.getBoundingClientRect();
  panel.style.left = `${Math.max(12, Math.min(box.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - 12))}px`;
  const top = box.bottom + 8 + panel.offsetHeight <= window.innerHeight - 12
    ? box.bottom + 8 : box.top - panel.offsetHeight - 8;
  panel.style.top = `${Math.max(12, Math.min(top, window.innerHeight - panel.offsetHeight - 12))}px`;
}

async function copyCurrentView() {
  if (document.querySelector("[data-share-view]")?.disabled
    || document.querySelector("#view").getAttribute("aria-busy") === "true" || state.failedRender) return;
  resetShareFeedback();
  const attempt = shareAttempt;
  const target = new URL(window.location.href);
  target.search = urlStateParameters().toString();
  target.hash = "";
  const token = state.renderToken;
  const status = document.querySelector("#share-status");
  const input = document.querySelector("#share-link");
  const button = document.querySelector("[data-share-view]");
  try {
    await navigator.clipboard.writeText(target.href);
    if (token !== state.renderToken || attempt !== shareAttempt) return;
    status.textContent = t("share.copied");
    button.classList.add("is-copied");
    button.setAttribute("title", t("share.copied"));
    button.setAttribute("aria-label", t("share.copied"));
    shareFeedbackTimer = setTimeout(resetShareFeedback, 1800);
  } catch {
    if (token !== state.renderToken || attempt !== shareAttempt) return;
    status.textContent = t("share.manual");
    input.value = target.href;
    input.hidden = false;
    document.querySelector("#share-fallback").hidden = false;
    positionShareFallback();
    input.focus({ preventScroll: true });
    input.select();
  }
}

document.addEventListener("click", event => {
  if (!document.querySelector("#share-fallback")?.hidden
    && !event.target.closest("#share-fallback, [data-share-view]")) resetShareFeedback();
});
window.addEventListener("resize", positionShareFallback);
document.addEventListener("scroll", positionShareFallback, { capture: true, passive: true });

function canonicalUrl() {
  const target = new URL(window.location.href);
  target.search = P8Metadata.canonicalParameters(urlStateParameters()).toString();
  target.hash = "";
  return target.href;
}

function updateDocumentMetadata() {
  const metadata = P8Metadata.metadataFor(I18n.language());
  const canonical = canonicalUrl();
  document.title = metadata.title;
  const values = {
    "#meta-description": metadata.description,
    "#og-title": metadata.title,
    "#og-description": metadata.description,
    "#og-url": canonical,
    "#og-locale": metadata.locale,
    "#twitter-title": metadata.title,
    "#twitter-description": metadata.description,
  };
  Object.entries(values).forEach(([selector, value]) => {
    const node = document.querySelector(selector);
    if (node) node.setAttribute("content", value);
  });
  const canonicalNode = document.querySelector("#canonical-url");
  if (canonicalNode) canonicalNode.href = canonical;
}

function renderSiteAttribution() {
  const node = document.querySelector("#site-attribution");
  if (!node) return;
  const footer = P8Metadata.metadataFor(I18n.language()).footer;
  node.replaceChildren();
  const scryfall = document.createElement("a");
  scryfall.href = "https://scryfall.com/";
  scryfall.target = "_blank";
  scryfall.rel = "noopener";
  scryfall.textContent = "Scryfall";
  const mtgch = document.createElement("a");
  mtgch.href = "https://mtgch.com/";
  mtgch.target = "_blank";
  mtgch.rel = "noopener";
  mtgch.textContent = "MTGCH";
  const policy = document.createElement("a");
  policy.href = "https://company.wizards.com/en/legal/fancontentpolicy";
  policy.target = "_blank";
  policy.rel = "noopener";
  policy.textContent = footer.policyLabel;
  node.append(
    document.createTextNode(`${footer.source} `),
    scryfall,
    document.createTextNode(` · ${footer.localizationSource} `),
    mtgch,
    document.createTextNode(` · ${footer.policyLead} `),
    policy,
    document.createTextNode(footer.policyTail)
  );
}

function hasExtendedUrlState(parameters) {
  return EXTENDED_URL_KEYS.some(key => parameters.has(key));
}

function currentDetailReveal() {
  const mobile = matchMedia("(max-width: 780px)").matches;
  if (state.product === "mtgo-landing" && state.landingFeatureDestination) {
    const destination = CSS.escape(state.landingFeatureDestination);
    return {
      selector: `[data-feature-destination="${destination}"]`,
      focusSelector: `[data-landing-feature-toggle="${destination}"]`,
      alignment: "start",
    };
  }
  if (state.product === "mtgo-landing" && state.landingSection === "features") {
    return { selector: "#features", focusSelector: null, alignment: "start" };
  }
  if (state.product === "mtgo-landing" && state.detailIdentity) {
    return {
      selector: `[data-landing-detail="${CSS.escape(state.detailIdentity)}"]`,
      alignment: "start",
    };
  }
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
  const target = captureRenderTarget();
  const preserveExistingContent = state.renderedViewKey === renderedViewKey(target)
    && root.childElementCount > 0
    && !root.querySelector(".loading-state, .error-state");
  const token = ++state.renderToken;
  const resourceReleases = [];
  let resourcesCommitted = false;
  const isCurrent = () => token === state.renderToken;
  discardPendingRefresh();
  // Navigation and URL describe the requested object even when loading fails.
  flushUrlWrite();
  document.querySelector("#payload-status").textContent = t("loading.data");
  const matrixPop = document.querySelector("#matrix-hover-pop");
  if (matrixPop) matrixPop.hidden = true;
  globalThis.P8CardImages?.cancelQueued("view");
  root.querySelectorAll(".inline-error-state, .load-error-row").forEach(node => node.remove());
  const share = document.querySelector("[data-share-view]");
  if (share) share.disabled = true;
  resetShareFeedback();
  root.setAttribute("aria-busy", "true");
  root.inert = true;
  document.querySelector(".view-loading-overlay")?.remove();
  const loadingOverlay = document.createElement("div");
  loadingOverlay.className = "view-loading-overlay";
  loadingOverlay.setAttribute("role", "status");
  loadingOverlay.textContent = t("loading.data");
  document.body.append(loadingOverlay);
  if (preserveExistingContent) {
    root.style.minHeight = `${Math.ceil(root.getBoundingClientRect().height)}px`;
  } else {
    state.renderedViewKey = null;
    currentContext = {};
    root.style.removeProperty("min-height");
    root.innerHTML = loadingSkeleton();
  }
  // Keep the previous lease until the replacement has acquired its resources;
  // scope/filter changes often need the same oversized document.
  try {
    await new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
    if (token !== state.renderToken) return;
    const [contract, localization] = await Promise.all([
      ensureClassifierNames(target.format),
      needsCardLocalization(target) ? MtgoController.loadCardLocalization() : null,
    ]);
    if (!isCurrent()) return;
    const request = Object.freeze({
      target, contract, isCurrent,
      retain(client, paths) {
        resourceReleases.push(client.retain(paths));
      },
      commit(render) {
        if (!isCurrent()) return null;
        // All view-local canonicalization, context and HTML creation below
        // are synchronous. No stale load can enter this commit section.
        state.classifierNameContract = contract;
        if (localization) state.cardLocalization = localization;
        const html = render();
        state.releaseViewResources?.();
        state.releaseViewResources = () => resourceReleases.forEach(release => release());
        resourcesCommitted = true;
        return html;
      },
    });
    let html;
    if (target.product === "mtgo-landing") html = await landingView(request);
    else if (target.product === "mtgo-statistics") html = await statsView(request);
    else if (target.product === "mtgo-matchups") html = await matchupView(request);
    else if (target.product === "mtgo-top8") html = await top8View(request);
    else if (target.product === "tabletop-major-events") html = await tabletopView(request);
    else throw new Error(`Unsupported product: ${target.product}`);
    if (token !== state.renderToken) return;
    root.innerHTML = html;
    state.renderedViewKey = renderedViewKey();
    if (!pendingUrlWrite) queueUrlWrite("replace");
    root.removeAttribute("aria-busy");
    root.inert = false;
    state.failedRender = null;
    if (share) share.disabled = false;
    if (!state.viewCheckedAt.has(currentViewKey())) {
      state.viewCheckedAt.set(currentViewKey(), Date.now());
    }
    updateFreshnessLayouts(root);
    globalThis.P8CardImages?.observe(root);
    restoreRenderPosition(root, focusSelector, position);
    updateMatrixStickyHeader();
    requestAnimationFrame(() => {
      if (!isCurrent()) return;
      updateFreshnessLayouts(root);
      restoreRenderPosition(root, focusSelector, position);
      root.style.removeProperty("min-height");
      requestAnimationFrame(() => {
        if (!isCurrent()) return;
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
      state.releaseViewResources?.();
      state.releaseViewResources = null;
      root.innerHTML = `<section class="error-state" role="alert">${retryMarkup()}</section>`;
      root.querySelector("button")?.focus({ preventScroll: true });
    }
    root.removeAttribute("aria-busy");
    root.inert = false;
    root.style.removeProperty("min-height");
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  } finally {
    if (!resourcesCommitted) resourceReleases.forEach(release => release());
    loadingOverlay.remove();
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
  state.landingFeatureOpen.clear();
  state.landingFeatureDestination = null;
  state.tabletopDetailIdentity = null;
  state.scrollHintsSeen.clear();
}

async function toggleDetailIdentity(identity) {
  const opening = state.detailIdentity !== identity;
  state.detailIdentity = opening ? identity : null;
  const parentId = identity.split("/", 1)[0];
  if (opening) setCompositionSelection(parentId);
  else if (state.compositionIdentity === parentId) setCompositionSelection(null);
  state.detailMode = "average";
  queueUrlWrite();
  await renderView();
}

document.addEventListener("click", async event => {
  const compositionButton = event.target.closest("button[data-composition-identity]");
  if (!compositionButton) clearTouchedComposition();
  const landingFeatureLink = event.target.closest("a[data-landing-feature-destination]");
  if (
    landingFeatureLink
    && !event.defaultPrevented
    && event.button === 0
    && !event.metaKey
    && !event.ctrlKey
    && !event.shiftKey
    && !event.altKey
  ) {
    event.preventDefault();
    discardPendingRefresh();
    const destination = landingFeatureLink.dataset.landingFeatureDestination;
    state.landingFeatureWeekFile = landingFeatureLink.dataset.landingFeatureWeek;
    state.landingFeatureOpen.clear();
    state.landingFeatureOpen.add(destination);
    state.landingFeatureDestination = destination;
    state.landingSection = "features";
    queueUrlWrite();
    await renderViewWithFocus(
      `[data-landing-feature-toggle="${CSS.escape(destination)}"]`,
      `[data-feature-destination="${CSS.escape(destination)}"]`,
      { revealAlignment: "start" }
    );
    return;
  }
  const button = event.target.closest("button");
  if (!button) {
    const landingRow = event.target.closest(".landing-environment-row[data-landing-row]");
    const cardLink = event.target.closest("a[data-card-image]");
    if (landingRow && !cardLink && matchMedia("(max-width: 780px)").matches) {
      await toggleDetailIdentity(landingRow.dataset.landingRow);
    }
    return;
  }
  if (button.hasAttribute("data-share-view")) {
    await copyCurrentView();
    return;
  }
  if (button.hasAttribute("data-return-to-top")) {
    const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    document.querySelector("#site-title")?.focus({ preventScroll: true });
    document.querySelector("#payload-status").textContent = t("navigation.returned_top");
    return;
  }
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
    const nextFormat = button.dataset.format;
    const available = availableProductIds(nextFormat);
    if (!available.length) {
      setMessage(t("availability.format", { format: formatLabel(nextFormat) }));
      return;
    }
    const nextProduct = available.includes(state.product) ? state.product : available[0];
    if (navigateToProductEntry(nextProduct, nextFormat)) return;
    state.format = nextFormat;
    state.product = nextProduct;
    resetInteractions();
    setMessage("");
    renderNavigation();
    queueUrlWrite();
    const reveal = currentDetailReveal();
    await renderViewWithFocus(null, reveal.selector, {
      revealAlignment: reveal.alignment,
    });
  } else if (button.dataset.product) {
    discardPendingRefresh();
    if (!productEntry(button.dataset.product)?.available) {
      setMessage(t("availability.product", {
        format: formatLabel(state.format),
        product: productLabel(button.dataset.product),
      }));
      return;
    }
    if (navigateToProductEntry(button.dataset.product, state.format)) return;
    state.product = button.dataset.product;
    state.landingSection = null;
    resetInteractions();
    setMessage("");
    renderNavigation();
    queueUrlWrite();
    const reveal = currentDetailReveal();
    await renderViewWithFocus(null, reveal.selector, {
      revealAlignment: reveal.alignment,
    });
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
      queueUrlWrite();
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
    const mobile = matchMedia("(max-width: 780px)").matches;
    const revealSelector = state.product === "mtgo-landing"
      ? `[data-landing-detail="${CSS.escape(action.identity)}"]`
      : mobile
        ? `[data-mobile-card-identity="${CSS.escape(action.identity)}"]`
        : ".deck-detail-row";
    await renderViewWithFocus(null, revealSelector, {
      revealAlignment: state.product === "mtgo-landing" || mobile ? "start" : "end",
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
    queueUrlWrite();
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
    queueUrlWrite();
    state.detailIdentity = null;
    if (!renderStatsExpansion(button)) await renderView();
  } else if (button.dataset.detailIdentity) {
    await toggleDetailIdentity(button.dataset.detailIdentity);
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
    queueUrlWrite();
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
    queueUrlWrite();
    await renderViewWithFocus("[data-matchup-filter-toggle]");
  } else if (button.hasAttribute("data-matchup-filter-cancel")) {
    const matchupDocument = currentContext.matchupDocument || currentContext.matchupDisplayDocument;
    if (matchupDocument) setMatchupFilterMenuOpen(false, matchupDocument);
  } else if (button.hasAttribute("data-matchup-filter-reset")) {
    state.matchupFilterIdentities = null;
    state.matchupRows.clear();
    state.matchupFilterOpen = false;
    queueUrlWrite();
    await renderViewWithFocus("[data-matchup-filter-toggle]");
  } else if (button.dataset.matchupRow) {
    const parentId = button.dataset.matchupRow;
    toggleSet(state.matchupRows, parentId);
    queueUrlWrite();
    await renderMatchupExpansion();
  } else if (button.dataset.matchupColumn) {
    const parentId = button.dataset.matchupColumn;
    toggleSet(state.matchupColumns, parentId);
    queueUrlWrite();
    await renderMatchupExpansion();
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
    queueUrlWrite();
    await renderMatchupExpansion();
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
    queueUrlWrite();
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
    queueUrlWrite();
    await renderView();
  } else if (button.dataset.landingFeatureToggle) {
    const destination = button.dataset.landingFeatureToggle;
    const opening = !state.landingFeatureOpen.has(destination);
    if (opening) {
      state.landingFeatureOpen.add(destination);
      state.landingFeatureDestination = destination;
      state.landingSection = "features";
    } else {
      state.landingFeatureOpen.delete(destination);
      if (state.landingFeatureDestination === destination) {
        state.landingFeatureDestination = null;
      }
    }
    queueUrlWrite();
    await renderViewWithFocus(
      `[data-landing-feature-toggle="${CSS.escape(destination)}"]`,
      opening ? `[data-feature-destination="${CSS.escape(destination)}"]` : null,
      { revealAlignment: "start" }
    );
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
    queueUrlWrite();
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
  } else if (event.target.id === "landing-feature-week") {
    discardPendingRefresh();
    state.landingFeatureWeekFile = event.target.value;
    state.landingFeatureOpen.clear();
    state.landingFeatureDestination = null;
    queueUrlWrite();
    await renderViewWithFocus("#landing-feature-week");
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
    queueUrlWrite();
    await renderView();
  }
});

function showMatrixTooltip(cell, x, y) {
  const pop = document.querySelector("#matrix-hover-pop");
  if (!pop) return;
  const box = cell.getBoundingClientRect();
  pop.textContent = cell.dataset.tooltip;
  pop.dataset.input = x == null ? "focus" : "pointer";
  pop.hidden = false;
  pop.style.left = `${Math.max(8, Math.min(window.innerWidth - pop.offsetWidth - 8, (x ?? box.left) + 12))}px`;
  pop.style.top = `${Math.max(8, (y ?? box.top) - pop.offsetHeight - 8)}px`;
}

document.addEventListener("mousemove", event => {
  const cell = event.target.closest("[data-record]");
  if (cell) showMatrixTooltip(cell, event.clientX, event.clientY);
});

document.addEventListener("mouseout", event => {
  const cell = event.target.closest("[data-record]");
  if (!cell || cell.contains(event.relatedTarget) || document.activeElement === cell) return;
  const pop = document.querySelector("#matrix-hover-pop");
  if (pop) pop.hidden = true;
});

document.addEventListener("focusin", event => {
  const cell = event.target.closest("[data-record]");
  if (!cell) return;
  showMatrixTooltip(cell);
});

document.addEventListener("click", event => {
  const cell = event.target.closest("[data-record]");
  if (!cell) {
    const pop = document.querySelector("#matrix-hover-pop");
    if (pop) pop.hidden = true;
    return;
  }
  showMatrixTooltip(cell);
});

document.addEventListener("scroll", () => {
  const pop = document.querySelector("#matrix-hover-pop");
  if (!pop || pop.hidden) return;
  const focusedCell = document.activeElement?.closest("[data-record]");
  if (pop.dataset.input === "focus" && focusedCell) {
    const box = focusedCell.getBoundingClientRect();
    if (box.bottom > 0 && box.top < window.innerHeight && box.right > 0 && box.left < window.innerWidth) {
      showMatrixTooltip(focusedCell);
      return;
    }
  }
  pop.hidden = true;
}, { capture: true, passive: true });

document.addEventListener("focusout", event => {
  if (!event.target.closest("[data-record]")) return;
  const pop = document.querySelector("#matrix-hover-pop");
  if (pop) pop.hidden = true;
});

function updateLanguageChrome(language) {
  I18n.setLanguage(language);
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = P8Metadata.metadataFor(language).title;
  const siteTitle = document.querySelector("#site-title");
  if (siteTitle) siteTitle.textContent = t("site.title");
  const zhButton = document.querySelector("#lang-zh");
  const enButton = document.querySelector("#lang-en");
  zhButton.classList.toggle("active", language === "zh");
  enButton.classList.toggle("active", language === "en");
  zhButton.setAttribute("aria-pressed", String(language === "zh"));
  enButton.setAttribute("aria-pressed", String(language === "en"));
  const returnToTop = document.querySelector("[data-return-to-top]");
  if (returnToTop) {
    const label = t("navigation.return_top");
    returnToTop.setAttribute("aria-label", label);
    returnToTop.setAttribute("title", label);
  }
  const shareButton = document.querySelector("[data-share-view]");
  if (shareButton) {
    shareButton.setAttribute("title", t("share.copy"));
    shareButton.setAttribute("aria-label", t("share.copy"));
  }
  const shareManual = document.querySelector('#share-fallback label');
  if (shareManual) shareManual.textContent = t("share.manual");
  const shareLink = document.querySelector("#share-link");
  if (shareLink) shareLink.setAttribute("aria-label", t("share.link"));
  renderSiteAttribution();
  updateDocumentMetadata();
}

async function changeLanguage(language) {
  discardPendingRefresh();
  P8Metadata.rememberLanguage(language, window.localStorage);
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
    const parameters = P8Metadata.normalizedRoute(new URLSearchParams(window.location.search));
    resetUrlBackedState();
    applyUrlState(parameters);
    if (navigateToProductEntry(state.product, state.format)) return;
    if (hasExtendedUrlState(parameters) || window.location.search !== `?${parameters}`) {
      queueUrlWrite("replace");
    }
    renderNavigation();
    const reveal = currentDetailReveal();
    await renderViewWithFocus(reveal.focusSelector || null, reveal.selector, {
      revealAlignment: reveal.alignment,
    });
  } catch (error) {
    state.failedRender = { error, preserveExistingContent: false };
    view.removeAttribute("aria-busy");
    const catalogFailure = !state.catalog;
    const errorMessage = typeof resourceErrorMessage === "function"
      ? resourceErrorMessage(error)
      : t("loading.unknown");
    view.innerHTML = `<section class="error-state" role="alert">
      <strong>${t(catalogFailure ? "loading.catalog_error" : "loading.initialization_error")}</strong>
      <p class="resource-error-message">${errorMessage}</p>
      <button class="secondary-button" type="button" data-retry-catalog>${t(catalogFailure
        ? "loading.catalog_retry"
        : "loading.initialization_retry")}</button>
    </section>`;
    view.querySelector("button")?.focus({ preventScroll: true });
    document.querySelector("#payload-status").textContent = t("loading.failed");
    console.error(error);
  }
}

window.addEventListener("popstate", async () => {
  if (!state.catalog) return;
  discardPendingRefresh();
  const rawParameters = new URLSearchParams(window.location.search);
  const parameters = P8Metadata.normalizedRoute(rawParameters);
  resetUrlBackedState();
  applyUrlState(parameters);
  if (navigateToProductEntry(state.product, state.format)) return;
  if (rawParameters.toString() !== parameters.toString()) queueUrlWrite("replace");
  setMessage("");
  renderNavigation();
  const reveal = currentDetailReveal();
  await renderViewWithFocus(reveal.focusSelector || null, reveal.selector, {
    revealAlignment: reveal.alignment,
  });
});

initialize();
