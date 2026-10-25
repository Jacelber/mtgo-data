"use strict";

const BACKGROUND_REFRESH_AGE_MS = 5 * 60 * 1000;

function currentViewKey(target = state) {
  const parts = [target.format, target.product];
  if (target.product === "mtgo-landing") parts.push(target.landingFeatureWeekFile || "latest");
  else if (target.product === "mtgo-statistics") parts.push(target.statsRange);
  else if (target.product === "mtgo-matchups") parts.push(target.matchupRange);
  else if (target.product === "mtgo-top8") parts.push(target.top8WeekFile || "latest");
  else if (target.product === "tabletop-major-events") {
    parts.push(target.tabletopEventId || "default", target.tabletopView, target.tabletopScope);
    if (target.tabletopView === "matchup") {
      parts.push([...target.tabletopSelectedEvents]
        .sort((left, right) => left.length - right.length || left.localeCompare(right))
        .join(","));
    }
  }
  return parts.join(":");
}

function renderedViewKey(target = state) {
  const presentation = target.product === "mtgo-statistics"
    ? [target.statsSort, target.statsDirection]
    : target.product === "tabletop-major-events" && target.tabletopView === "overview"
      ? [target.tabletopSort, target.tabletopDirection]
      : [target.matchupMainstreamOnly, [...(target.matchupFilterIdentities || [])].sort()];
  return JSON.stringify([currentViewKey(target), target.language || I18n.language(), presentation]);
}

function captureRenderTarget() {
  // Only request inputs belong here. All arrays are copied and frozen so a
  // navigation cannot change the meaning of an in-flight load.
  const keys = [
    "format", "product", "statsRange", "matchupRange", "matchupMainstreamOnly",
    "detailIdentity", "top8WeekFile", "top8Detail", "landingFeatureWeekFile",
    "landingFeatureDestination", "tabletopView", "tabletopEventId",
    "tabletopDetailIdentity", "tabletopScope", "statsSort", "statsDirection",
    "tabletopSort", "tabletopDirection",
  ];
  return Object.freeze({
    ...Object.fromEntries(keys.map(key => [key, state[key]])),
    path: productEntry()?.path,
    language: I18n.language(),
    landingFeatureOpen: Object.freeze([...state.landingFeatureOpen]),
    tabletopSelectedEvents: Object.freeze([...state.tabletopSelectedEvents]),
    matchupFilterIdentities: state.matchupFilterIdentities === null
      ? null : Object.freeze([...state.matchupFilterIdentities]),
  });
}

function needsCardLocalization(target) {
  if (target.language !== "zh") return false;
  if (target.product === "mtgo-landing") return true;
  if (target.product === "mtgo-statistics") return Boolean(target.detailIdentity);
  if (target.product === "mtgo-top8") return Boolean(target.top8Detail);
  return target.product === "tabletop-major-events"
    && target.tabletopView === "overview" && Boolean(target.tabletopDetailIdentity);
}

function loadingSkeleton() {
  return `<section class="loading-skeleton" aria-hidden="true">
    <span class="skeleton-line skeleton-title"></span>
    <div class="skeleton-summary">${Array.from(
      { length: 3 },
      () => '<span class="skeleton-block"></span>'
    ).join("")}</div>
    <div class="skeleton-rows">${Array.from(
      { length: 5 },
      () => '<span class="skeleton-line"></span>'
    ).join("")}</div>
  </section><p class="sr-only loading-state">${t("loading.data")}</p>`;
}

function resourceErrorMessage(error) {
  if (navigator.onLine === false) return t("loading.offline");
  if (error?.code === "timeout") return t("loading.timeout");
  if (error?.code === "http") return t("loading.http_error");
  if (error?.code === "invalid") return t("loading.invalid");
  return t("loading.generic");
}

function retryMarkup({ catalog = false, detail = false } = {}) {
  const attribute = catalog ? "data-retry-catalog" : "data-retry-view";
  return `<strong>${detail ? t("loading.detail_error") : t("loading.error")}</strong>
    <p class="resource-error-message">${resourceErrorMessage(state.failedRender?.error)}</p>
    <button class="secondary-button" type="button" ${attribute}>${catalog
      ? t("loading.catalog_retry")
      : t("loading.retry")}</button>`;
}

function placeScopedError(root, focusSelector) {
  root.querySelectorAll(".inline-error-state, .load-error-row").forEach(node => node.remove());
  const target = renderTarget(root, focusSelector);
  const row = target?.closest("tr");
  if (row) {
    const errorRow = document.createElement("tr");
    errorRow.className = "deck-detail-row load-error-row";
    const cell = document.createElement("td");
    cell.colSpan = Math.max(1, row.cells.length);
    cell.innerHTML = `<div class="inline-error-state" role="alert">${retryMarkup({ detail: true })}</div>`;
    errorRow.append(cell);
    row.insertAdjacentElement("afterend", errorRow);
    errorRow.querySelector("button")?.focus({ preventScroll: true });
    return;
  }
  const anchor = target?.closest(".mobile-metric-card, .landing-feature-item, .panel") || target;
  const error = document.createElement("div");
  error.className = "inline-error-state";
  error.setAttribute("role", "alert");
  error.innerHTML = retryMarkup({ detail: true });
  if (anchor) anchor.insertAdjacentElement("afterend", error);
  else root.prepend(error);
  error.querySelector("button")?.focus({ preventScroll: true });
}

function focusViewTitle(root) {
  const headings = [...root.querySelectorAll("h2, h3")];
  const title = headings.find(node => node.getClientRects().length) || headings[0];
  if (!title) return;
  title.setAttribute("tabindex", "-1");
  title.focus({ preventScroll: true });
  title.scrollIntoView({ block: "nearest" });
}

function refreshStatus() {
  return document.querySelector("#refresh-status");
}

function showRefreshStatus(kind, message, action = null) {
  const node = refreshStatus();
  if (!node) return;
  node.dataset.kind = kind;
  node.hidden = false;
  node.innerHTML = `<span>${message}</span>${action
    ? ` <button class="secondary-button" type="button" ${action.attribute}>${action.label}</button>`
    : ""}`;
}

function clearRefreshStatus() {
  const node = refreshStatus();
  if (!node) return;
  node.hidden = true;
  node.replaceChildren();
  delete node.dataset.kind;
}

async function stageCurrentRefresh() {
  const target = captureRenderTarget();
  const context = currentContext;
  const namesPath = `stats/${target.format}/archetype_names.json`;
  const names = await classifierNameClient.stage([namesPath]);
  const contract = ArchetypeNames.normalize(names.get(namesPath), target.format);
  const data = await stageViewRefresh(target, context, contract);
  if (!data) return null;
  ArchetypeNames.validateCoverage(contract, Object.values(data.values));
  return Object.freeze({
    changed: names.changed || data.changed,
    commit() {
      // Both groups have passed validation. The caller guards view identity
      // and render token before this synchronous commit.
      data.commit();
      names.commit();
      state.classifierNameContracts.set(target.format, contract);
      state.classifierNameContract = contract;
    },
  });
}

async function stageViewRefresh(target, context, contract) {
  if (target.product === "mtgo-landing") {
    return MtgoController.stageLanding(
      target.format,
      target.path,
      target.landingFeatureWeekFile,
      {
        includeEnvironmentDecks: Boolean(target.detailIdentity),
        includeFeatureDecks: Boolean(
          target.landingFeatureOpen.length || target.landingFeatureDestination
        ),
      }
    );
  }
  if (target.product === "mtgo-statistics") {
    return MtgoController.stageStatistics(target.format, target.statsRange, {
      includeDecks: Boolean(target.detailIdentity),
    });
  }
  if (target.product === "mtgo-matchups") {
    return MtgoController.stageMatchup(target.format, target.matchupRange, {
      includeRange: target.matchupMainstreamOnly,
    });
  }
  if (target.product === "mtgo-top8" && target.top8WeekFile) {
    const week = context.top8Index?.weeks?.find(
      item => item.file === target.top8WeekFile
    );
    return MtgoController.stageTop8(target.path, target.top8WeekFile, {
      comparisonBasesFile: target.top8Detail
        ? week?.comparison_bases_file
        : null,
    });
  }
  if (target.product === "tabletop-major-events" && context.eventEntry) {
    return TabletopController.stageEvent(
      target.path,
      context.eventEntry,
      target.format,
      MtgoController,
      {
        includeMatchup: target.tabletopView === "matchup",
        includeDecks: target.tabletopView === "overview"
          && Boolean(target.tabletopDetailIdentity),
        selectedEventEntries: context.selectedEventEntries,
        canonicalIdentityOrder: [...contract.names.keys(), "unknown"],
      }
    );
  }
  return null;
}

async function checkForUpdates() {
  if (state.refreshInProgress || state.pendingRefresh
      || state.renderedViewKey !== renderedViewKey()
      || document.querySelector("#view").getAttribute("aria-busy") === "true") return;
  state.refreshInProgress = true;
  showRefreshStatus("loading", t("loading.checking"));
  const key = currentViewKey();
  const token = state.renderToken;
  const isCurrent = () => token === state.renderToken && key === currentViewKey();
  try {
    const staged = await stageCurrentRefresh();
    if (!isCurrent()) return;
    if (!staged) {
      clearRefreshStatus();
      return;
    }
    if (staged.changed) {
      state.pendingRefresh = { key, token, staged };
      showRefreshStatus("available", t("loading.update_available"), {
        attribute: "data-apply-refresh",
        label: t("loading.apply_update"),
      });
    } else {
      staged.commit();
      state.viewCheckedAt.set(key, Date.now());
      clearRefreshStatus();
    }
  } catch (error) {
    if (!isCurrent()) return;
    showRefreshStatus("error", t("loading.refresh_failed"), {
      attribute: "data-retry-refresh",
      label: t("loading.retry"),
    });
    console.error(error);
  } finally {
    state.refreshInProgress = false;
  }
}

function commitPendingRefresh() {
  if (!state.pendingRefresh) return;
  if (state.pendingRefresh.key !== currentViewKey()
      || state.pendingRefresh.token !== state.renderToken) {
    discardPendingRefresh();
    return;
  }
  state.pendingRefresh.staged.commit();
  state.viewCheckedAt.set(state.pendingRefresh.key, Date.now());
  state.pendingRefresh = null;
  clearRefreshStatus();
}

function discardPendingRefresh() {
  state.pendingRefresh = null;
  clearRefreshStatus();
}

document.addEventListener("visibilitychange", async () => {
  if (document.visibilityState !== "visible" || !state.catalog) return;
  const checkedAt = state.viewCheckedAt.get(currentViewKey()) || 0;
  if (Date.now() - checkedAt >= BACKGROUND_REFRESH_AGE_MS) {
    await checkForUpdates();
  }
});

window.addEventListener("online", () => {
  document.querySelector("#payload-status").textContent = t("loading.online");
  if (refreshStatus()?.dataset.kind === "error") {
    showRefreshStatus("error", t("loading.online"), {
      attribute: "data-retry-refresh",
      label: t("loading.retry"),
    });
  }
  const error = document.querySelector(".error-state, .inline-error-state");
  if (error && !error.querySelector(".network-online-note")) {
    const note = document.createElement("p");
    note.className = "network-online-note";
    note.textContent = t("loading.online");
    error.querySelector("button")?.insertAdjacentElement("beforebegin", note);
  }
});
