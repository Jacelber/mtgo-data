"use strict";

const BACKGROUND_REFRESH_AGE_MS = 5 * 60 * 1000;

function currentViewKey() {
  const parts = [state.format, state.product];
  if (state.product === "mtgo-statistics") parts.push(state.statsRange);
  else if (state.product === "mtgo-matchups") parts.push(state.matchupRange);
  else if (state.product === "mtgo-top8") parts.push(state.top8WeekFile || "latest");
  else if (state.product === "weekly-pickup") parts.push(state.pickupWeekFile || "latest");
  else if (state.product === "tabletop-major-events") {
    parts.push(state.tabletopEventId || "default", state.tabletopView);
  }
  return parts.join(":");
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
  const anchor = target?.closest(".mobile-metric-card, .pickup-card, .panel") || target;
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
  if (state.product === "mtgo-statistics") {
    return MtgoController.stageStatistics(state.format, state.statsRange, {
      includeDecks: Boolean(state.detailIdentity),
    });
  }
  if (state.product === "mtgo-matchups") {
    return MtgoController.stageMatchup(state.format, state.matchupRange);
  }
  if (state.product === "mtgo-top8" && state.top8WeekFile) {
    const week = currentContext.top8Index?.weeks?.find(
      item => item.file === state.top8WeekFile
    );
    return MtgoController.stageTop8(productEntry().path, state.top8WeekFile, {
      comparisonBasesFile: state.top8Detail
        ? week?.comparison_bases_file
        : null,
    });
  }
  if (state.product === "weekly-pickup" && state.pickupWeekFile) {
    return MtgoController.stagePickup(productEntry().path, state.pickupWeekFile);
  }
  if (state.product === "tabletop-major-events" && currentContext.eventEntry) {
    return TabletopController.stageEvent(
      productEntry().path,
      currentContext.eventEntry,
      state.format,
      MtgoController,
      {
        includeMatchup: state.tabletopView === "matchup",
        includeDecks: state.tabletopView === "overview"
          && Boolean(state.tabletopDetailIdentity),
      }
    );
  }
  return null;
}

async function checkForUpdates() {
  if (state.refreshInProgress || state.pendingRefresh) return;
  state.refreshInProgress = true;
  showRefreshStatus("loading", t("loading.checking"));
  const key = currentViewKey();
  try {
    const staged = await stageCurrentRefresh();
    if (!staged) {
      clearRefreshStatus();
      return;
    }
    if (staged.changed) {
      state.pendingRefresh = { key, staged };
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
  state.pendingRefresh.staged.commit();
  state.viewCheckedAt.set(state.pendingRefresh.key, Date.now());
  state.pendingRefresh = null;
  clearRefreshStatus();
}

function discardPendingRefresh() {
  if (!state.pendingRefresh) return;
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
