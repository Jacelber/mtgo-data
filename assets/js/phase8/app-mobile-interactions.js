"use strict";

let lastResponsiveFocusKey = null;

function renderFocusSelector(element, root) {
  if (!element || !root.contains(element)) return null;
  if (element.id) return `#${CSS.escape(element.id)}`;
  const attributes = [...element.attributes];
  const stableAttribute = attributes.find(attribute => attribute.name === "data-responsive-key")
    || attributes.find(attribute => (
      attribute.name.startsWith("data-")
      && attribute.name !== "data-tooltip"
      && attribute.name !== "data-tip"
    ));
  return stableAttribute
    ? `[${stableAttribute.name}="${CSS.escape(stableAttribute.value)}"]`
    : null;
}

function renderTarget(root, selector) {
  if (!selector) return null;
  const targets = [...root.querySelectorAll(selector)];
  return targets.find(target => target.getClientRects().length) || targets[0] || null;
}

function restoreRenderFocus(root, selector) {
  if (!selector) return;
  renderTarget(root, selector)?.focus({ preventScroll: true });
}

function captureRenderPosition(root, selector) {
  const anchor = renderTarget(root, selector);
  return {
    anchorTop: anchor?.getBoundingClientRect().top ?? null,
    scrollY: window.scrollY,
    scrollers: [...root.querySelectorAll(".table-scroll")].map(scroller => ({
      left: scroller.scrollLeft,
      top: scroller.scrollTop,
    })),
  };
}

function restoreRenderPosition(root, selector, position) {
  [...root.querySelectorAll(".table-scroll")].forEach((scroller, index) => {
    const saved = position.scrollers[index];
    if (!saved) return;
    scroller.scrollLeft = saved.left;
    scroller.scrollTop = saved.top;
  });
  const anchor = renderTarget(root, selector);
  if (anchor && position.anchorTop !== null) {
    window.scrollBy(0, anchor.getBoundingClientRect().top - position.anchorTop);
  } else {
    window.scrollTo(0, position.scrollY);
  }
}

function renderStatsExpansion(trigger) {
  const root = document.querySelector("#view");
  const body = root.querySelector(".data-table.metric-columns tbody");
  if (!body || !currentContext?.range) return false;
  const focusSelector = renderFocusSelector(trigger, root);
  const position = captureRenderPosition(root, focusSelector);
  const groups = statisticsGroups(sortedArchetypes(currentContext.range.archetypes));
  body.innerHTML = statsRows(groups);
  const mobileList = root.querySelector(".mobile-metric-list");
  if (mobileList) mobileList.outerHTML = statsCards(groups);
  const expandAll = root.querySelector("#stats-expand-all");
  if (expandAll) {
    expandAll.textContent = state.statsExpanded.size
      ? t("stats.hide_subtypes")
      : t("stats.show_subtypes");
  }
  restoreRenderPosition(root, focusSelector, position);
  restoreRenderFocus(root, focusSelector);
  flushUrlWrite();
  return true;
}

function revealExpandedContent(root, selector, alignment = "end") {
  if (!selector) return;
  const target = renderTarget(root, selector);
  if (!target) return;
  const rect = target.getBoundingClientRect();
  const viewportMargin = 24;
  const viewportBottom = window.innerHeight - viewportMargin;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (alignment === "start") {
    const offset = rect.top - viewportMargin;
    if (Math.abs(offset) <= 1) return;
    window.scrollBy({ top: offset, behavior: reduceMotion ? "auto" : "smooth" });
    return;
  }
  if (rect.top >= viewportMargin && rect.bottom <= viewportBottom) return;
  const targetFitsViewport = rect.height <= window.innerHeight - (viewportMargin * 2);
  const offset = targetFitsViewport && rect.top < viewportMargin
    ? rect.top - viewportMargin
    : rect.bottom - viewportBottom;
  window.scrollBy({ top: offset, behavior: reduceMotion ? "auto" : "smooth" });
}

function announceMobileSort(kind) {
  const select = document.querySelector(`[data-mobile-${kind}-sort]`);
  if (!select) return;
  const direction = kind === "stats" ? state.statsDirection : state.tabletopDirection;
  document.querySelector("#payload-status").textContent = t("mobile.sorted", {
    field: select.selectedOptions[0]?.textContent || "",
    direction: t(direction === "asc" ? "mobile.ascending" : "mobile.descending"),
  });
}

async function handleMobileListClick(button) {
  if (button.dataset.mobileStatsToggle) {
    const parentId = button.dataset.mobileStatsToggle;
    const opening = !state.statsExpanded.has(parentId);
    toggleSet(state.statsExpanded, parentId);
    if (opening) setCompositionSelection(parentId);
    else if (state.compositionIdentity === parentId) setCompositionSelection(null);
    if (state.detailIdentity) queueUrlWrite();
    state.detailIdentity = null;
    const revealSelector = opening
      ? `[data-mobile-card-identity="${CSS.escape(parentId)}"]`
      : null;
    if (renderStatsExpansion(button)) {
      revealExpandedContent(document.querySelector("#view"), revealSelector, "start");
    } else {
      await renderViewWithFocus(null, revealSelector, { revealAlignment: "start" });
    }
    return true;
  }
  if (button.dataset.mobileStatsDetail) {
    const identity = button.dataset.mobileStatsDetail;
    const opening = state.detailIdentity !== identity;
    state.detailIdentity = opening ? identity : null;
    const parentId = identity.split("/", 1)[0];
    if (opening) setCompositionSelection(parentId);
    else if (state.compositionIdentity === parentId) setCompositionSelection(null);
    state.detailMode = "average";
    queueUrlWrite();
    await renderViewWithFocus(
      null,
      opening ? `[data-mobile-expanded-content="stats:${CSS.escape(identity)}"]` : null,
      { revealAlignment: "start" }
    );
    return true;
  }
  if (button.hasAttribute("data-close-mobile-stats-detail")) {
    const identity = state.detailIdentity;
    state.detailIdentity = null;
    if (state.compositionIdentity === identity?.split("/", 1)[0]) {
      setCompositionSelection(null);
    }
    queueUrlWrite();
    await renderViewWithFocus(`[data-mobile-stats-detail="${CSS.escape(identity || "")}"]`);
    return true;
  }
  if (button.hasAttribute("data-mobile-stats-direction")) {
    state.statsDirection = state.statsDirection === "desc" ? "asc" : "desc";
    queueUrlWrite();
    await renderView();
    announceMobileSort("stats");
    return true;
  }
  if (button.dataset.mobileTabletopToggle) {
    const parentId = button.dataset.mobileTabletopToggle;
    const opening = !state.tabletopExpanded.has(parentId);
    toggleSet(state.tabletopExpanded, parentId);
    state.tabletopDetailIdentity = null;
    await renderViewWithFocus(null, opening
      ? `[data-mobile-expanded-content="tabletop-subtypes:${CSS.escape(parentId)}"]`
      : null);
    return true;
  }
  if (button.dataset.mobileTabletopDetail) {
    const identity = button.dataset.mobileTabletopDetail;
    const opening = state.tabletopDetailIdentity !== identity;
    state.tabletopDetailIdentity = opening ? identity : null;
    state.detailMode = "average";
    queueUrlWrite();
    await renderViewWithFocus(null, opening
      ? `[data-mobile-expanded-content="tabletop:${CSS.escape(identity)}"]`
      : null);
    return true;
  }
  if (button.hasAttribute("data-close-mobile-tabletop-detail")) {
    const identity = state.tabletopDetailIdentity;
    state.tabletopDetailIdentity = null;
    queueUrlWrite();
    await renderViewWithFocus(`[data-mobile-tabletop-detail="${CSS.escape(identity || "")}"]`);
    return true;
  }
  if (button.hasAttribute("data-mobile-tabletop-direction")) {
    state.tabletopDirection = state.tabletopDirection === "desc" ? "asc" : "desc";
    queueUrlWrite();
    await renderView();
    announceMobileSort("tabletop");
    return true;
  }
  return false;
}

async function handleMobileListChange(target) {
  if (target.hasAttribute("data-mobile-stats-sort")) {
    state.statsSort = target.value;
    state.statsDirection = state.statsSort === "name" ? "asc" : "desc";
    queueUrlWrite();
    await renderViewWithFocus("#stats-mobile-sort");
    announceMobileSort("stats");
    return true;
  }
  if (target.hasAttribute("data-mobile-tabletop-sort")) {
    state.tabletopSort = target.value;
    state.tabletopDirection = state.tabletopSort === "name" ? "asc" : "desc";
    queueUrlWrite();
    await renderViewWithFocus("#tabletop-mobile-sort");
    announceMobileSort("tabletop");
    return true;
  }
  return false;
}

function updateMatrixRowClipping() {
  document.querySelectorAll(".matrix-scroll .row-axis-name").forEach(name => {
    name.classList.remove("is-clipped");
    name.classList.toggle("is-clipped", name.scrollHeight > name.clientHeight + 1);
  });
}

function updateMatrixStickyHeader() {
  const scroller = document.querySelector(".matrix-scroll[data-scroll-hint-key]");
  const sticky = scroller?.closest(".horizontal-scroll-frame")?.querySelector("[data-matrix-sticky]");
  const sourceTable = scroller?.querySelector(".matchup-table");
  const sourceHeader = sourceTable?.querySelector("thead");
  const stickyViewport = sticky?.querySelector(".matrix-sticky-viewport");
  if (!scroller || !sticky || !sourceTable || !sourceHeader || !stickyViewport) return;

  stickyViewport.scrollLeft = scroller.scrollLeft;
  const headerRect = sourceHeader.getBoundingClientRect();
  const tableRect = sourceTable.getBoundingClientRect();
  const stickyHeight = stickyViewport.getBoundingClientRect().height;
  sticky.classList.toggle("active", headerRect.top <= 0 && tableRect.bottom > stickyHeight);
}

function updateMatrixPresentation() {
  updateMatrixRowClipping();
  updateMatrixStickyHeader();
}

document.addEventListener("focusin", event => {
  if (event.target.dataset.responsiveKey) {
    lastResponsiveFocusKey = event.target.dataset.responsiveKey;
  }
});

document.addEventListener("scroll", event => {
  const scroller = event.target.closest?.("[data-scroll-hint-key]");
  if (!scroller) return;
  updateMatrixStickyHeader();
  if (scroller.scrollLeft <= 4) return;
  state.scrollHintsSeen.add(scroller.dataset.scrollHintKey);
  scroller.closest(".horizontal-scroll-frame")?.classList.add("hint-dismissed");
}, true);

const mobileMetricQuery = matchMedia("(max-width: 780px)");
function transferResponsiveFocus() {
  const active = document.activeElement;
  const key = active?.dataset.responsiveKey || lastResponsiveFocusKey;
  if (!key) return;
  requestAnimationFrame(() => {
    const selector = `[data-responsive-key="${CSS.escape(key)}"]`;
    const target = renderTarget(document.querySelector("#view"), selector);
    if (target && target !== active) target.focus({ preventScroll: true });
  });
}
mobileMetricQuery.addEventListener("change", transferResponsiveFocus);
window.addEventListener("resize", transferResponsiveFocus);
window.addEventListener("resize", updateMatrixPresentation);
window.addEventListener("scroll", updateMatrixStickyHeader, { passive: true });
