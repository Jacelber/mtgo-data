"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { expect, test } = require("@playwright/test");

const OPTIONAL_CARD_LOCALIZATION_PATH = "/assets/card-localization/cards.json";

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(process.cwd(), relativePath), "utf8"));
}

function isOptionalCardLocalizationRequest(url) {
  return new URL(url).pathname === OPTIONAL_CARD_LOCALIZATION_PATH;
}

function resolveTabletopSubject() {
  const requestedFormat = (process.env.TABLETOP_CANDIDATE_FORMAT || "").trim();
  const requestedEventId = (process.env.TABLETOP_CANDIDATE_EVENT_ID || "").trim();
  if (Boolean(requestedFormat) !== Boolean(requestedEventId)) {
    throw new Error("Tabletop candidate format and event ID must be supplied together");
  }

  const formatId = requestedFormat || "modern";
  const consumerCatalog = readJson("stats/catalog.json");
  const formatEntry = consumerCatalog.formats?.find(item => item.id === formatId);
  const product = formatEntry?.products?.find(item => item.id === "tabletop-major-events");
  if (!product?.available || typeof product.path !== "string") {
    throw new Error(`Tabletop product is unavailable for ${formatId}`);
  }

  const indexPath = product.path;
  const index = readJson(indexPath);
  if (index.format !== formatId || !Array.isArray(index.events)) {
    throw new Error(`Tabletop event catalog is invalid for ${formatId}`);
  }
  const defaultEntry = index.events.find(item => item.event_id === index.default_event_id);
  const candidateEventId = requestedEventId || index.default_event_id;
  const candidateEntry = index.events.find(item => item.event_id === candidateEventId);
  if (!defaultEntry || !candidateEntry) {
    throw new Error("Tabletop default or candidate event is absent from the event catalog");
  }

  const eventRoot = path.posix.dirname(indexPath);
  const overview = readJson(path.posix.join(eventRoot, candidateEntry.overview));
  const quality = readJson(path.posix.join(eventRoot, candidateEntry.quality));
  const overviewScope = candidateEntry.default_scope;
  if (!overviewScope || !overview.scopes?.[overviewScope]) {
    throw new Error("Tabletop candidate has no renderable default Overview scope");
  }
  let matchupScope = null;
  if (typeof candidateEntry.matchup === "string") {
    const matchup = readJson(path.posix.join(eventRoot, candidateEntry.matchup));
    matchupScope = candidateEntry.scope_order?.find(scope => matchup.scopes?.[scope]) || null;
  }

  return {
    candidateEntry,
    candidateEventId,
    defaultEntry,
    formatId,
    matchupScope,
    overviewScope,
    quality,
  };
}

function declaredQualityIssue(quality, code) {
  const issue = quality.issues?.find(item => item.code === code);
  if (!issue) return null;
  if (!Number.isInteger(issue.count) || issue.count <= 0) {
    throw new Error(`Tabletop quality issue ${code} has no positive count`);
  }
  return issue;
}

async function expectPublishedNumber(page, metric) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator(`[data-freshness-key="${metric}"]`)).toContainText(/\d/);
}

async function expectTabletopRendered(page) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0, { timeout: 10_000 });
  await expect(
    page.locator("#view .error-state, #view .inline-error-state, #view .load-error-row")
  ).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator("#view")).not.toContainText(/\b(?:NaN|undefined)\b/);
}

test("MTGO entry renders candidate-derived data", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expectPublishedNumber(page, "decks");
});

test("legacy Weekly Pickup path renders the admitted Landing feature", async ({ page, request }) => {
  const response = await request.get("/stats/standard/mtgo/landing/current.json");
  expect(response.ok()).toBe(true);
  const landing = await response.json();
  expect(Array.isArray(landing.features?.items)).toBe(true);
  const expectedFeatureCount = landing.features.items.length;

  await page.goto("/index.html?format=standard&product=weekly-pickup&lang=zh");
  await expect(page).toHaveURL(/product=mtgo-landing/);
  const normalizedUrl = new URL(page.url());
  expect(normalizedUrl.searchParams.get("format")).toBe("standard");
  expect(normalizedUrl.searchParams.get("product")).toBe("mtgo-landing");
  expect(normalizedUrl.searchParams.get("section")).toBe("features");
  expect(normalizedUrl.searchParams.get("lang")).toBe("zh");
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator(".landing-features")).toBeVisible();
  await expect(page.locator(".landing-feature-item")).toHaveCount(expectedFeatureCount);
  const emptyState = page.locator(".landing-feature-content .landing-empty");
  if (expectedFeatureCount === 0) await expect(emptyState).toBeVisible();
  else await expect(emptyState).toHaveCount(0);
});

test("Tabletop entry renders candidate-derived data", async ({ page }) => {
  const subject = resolveTabletopSubject();
  const runtimeErrors = [];
  page.on("pageerror", error => runtimeErrors.push(`pageerror: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource:")) {
      runtimeErrors.push(`console.error: ${message.text()}`);
    }
  });
  page.on("response", response => {
    if (response.status() >= 400 && !isOptionalCardLocalizationRequest(response.url())) {
      runtimeErrors.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  page.on("requestfailed", request => {
    if (!isOptionalCardLocalizationRequest(request.url())) {
      runtimeErrors.push(`request failed: ${request.url()}`);
    }
  });

  await page.goto(
    `/melee/index.html?format=${encodeURIComponent(subject.formatId)}`
      + "&product=tabletop-major-events&view=overview&lang=en"
  );
  await expectTabletopRendered(page);
  await expect(page.locator("#tabletop-event")).toHaveValue(subject.defaultEntry.event_id);
  await expect(page.locator(".event-summary")).toContainText(subject.defaultEntry.name);

  await page.goto(
    `/melee/index.html?format=${encodeURIComponent(subject.formatId)}`
      + `&product=tabletop-major-events&view=overview&event=${encodeURIComponent(subject.candidateEventId)}`
      + `&scope=${encodeURIComponent(subject.overviewScope)}&lang=en`
  );
  await expectTabletopRendered(page);
  await expect(page.locator("#tabletop-event")).toHaveValue(subject.candidateEventId);
  await expect(page.locator(".event-summary")).toContainText(subject.candidateEntry.name);
  await expectPublishedNumber(page, "scope-decks");

  const unknown = declaredQualityIssue(subject.quality, "unknown_classifications");
  if (unknown) {
    await expect(
      page.locator(".identity-label").filter({ hasText: /^Unknown$/ }).first()
    ).toBeVisible();
  }
  const unavailable = declaredQualityIssue(
    subject.quality,
    "missing_or_unavailable_decklists"
  );
  if (unavailable) {
    const notice = page.locator(".quality-notice li").filter({
      hasText: /no available decklist/i,
    });
    await expect(notice).toContainText(String(unavailable.count));
  }

  if (subject.matchupScope) {
    await page.goto(
      `/melee/index.html?format=${encodeURIComponent(subject.formatId)}`
        + `&product=tabletop-major-events&view=matchup&event=${encodeURIComponent(subject.candidateEventId)}`
        + `&events=${encodeURIComponent(subject.candidateEventId)}`
        + `&scope=${encodeURIComponent(subject.matchupScope)}&lang=en`
    );
    await expectTabletopRendered(page);
    await expect(
      page.locator(`[data-tabletop-event-check="${subject.candidateEventId}"]`)
    ).toBeChecked();
  }
  expect(runtimeErrors).toEqual([]);
});
