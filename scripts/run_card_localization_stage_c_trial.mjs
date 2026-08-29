#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import {
  mkdir,
  readFile,
  rename,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const require = createRequire(import.meta.url);
const playwrightVersion = require("@playwright/test/package.json").version;
const scriptPath = fileURLToPath(import.meta.url);
const defaultRepositoryRoot = path.resolve(path.dirname(scriptPath), "..");

const STATE_FILE = "trial-state.json";
const PLAN_FILE = "exact-plan.json";
const SCHEMA_VERSION = "1.0.0";
const MAX_SAMPLE = 100;
const MAX_LOGICAL = 200;
const MAX_PHYSICAL = 400;
const CONTROLLER_CONSTANTS = Object.freeze({
  MAX_CONCURRENT_IMAGES: "1",
  MAX_IMAGE_ATTEMPTS: "2",
  MIN_IMAGE_START_INTERVAL_MS: "150",
  IMAGE_ATTEMPT_TIMEOUT_MS: "15_000",
  IMAGE_RETRY_DELAY_MS: "1_500",
});

export class StageCContractError extends Error {
  constructor(code) {
    super(code);
    this.name = "StageCContractError";
    this.code = code;
  }
}

function fail(code) {
  throw new StageCContractError(code);
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map(key => [key, stableValue(value[key])])
    );
  }
  return value;
}

function stableJson(value) {
  return JSON.stringify(stableValue(value));
}

function isHexDigest(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isInside(candidate, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== "..");
}

function isLoopback(hostname) {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1";
}

function checkedUrl(raw, { fixtureMode, provider }) {
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    fail("invalid_url");
  }
  if (parsed.username || parsed.password || !parsed.pathname) fail("unsafe_url");
  if (fixtureMode) {
    if (!isLoopback(parsed.hostname) || !["http:", "https:"].includes(parsed.protocol)) {
      fail("fixture_non_loopback_url");
    }
    return parsed;
  }
  if (parsed.protocol !== "https:") fail("non_https_url");
  if (provider === "source" && parsed.hostname !== "images.mtgch.com") {
    fail("unexpected_source_host");
  }
  if (provider === "control" && !parsed.hostname.endsWith(".scryfall.io")) {
    fail("unexpected_control_host");
  }
  return parsed;
}

function cleanRelativePath(value, code) {
  if (typeof value !== "string" || !value.startsWith("/") || value.includes("\\")) {
    fail(code);
  }
  const parsed = new URL(value, "https://contract.invalid");
  if (parsed.origin !== "https://contract.invalid" || parsed.search || parsed.hash) fail(code);
  return parsed.pathname;
}

export function parseArguments(argv) {
  const [command, ...rest] = argv;
  if (!["prepare", "session", "finalize"].includes(command)) fail("unknown_command");
  const allowed = {
    prepare: new Set(["trial_dir", "pages_url", "plan_input"]),
    session: new Set(["trial_dir", "number"]),
    finalize: new Set(["trial_dir", "aggregate_out"]),
  }[command];
  const values = { command, fixtureMode: false };
  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (token === "--fixture-mode") {
      values.fixtureMode = true;
      continue;
    }
    if (!token.startsWith("--") || index + 1 >= rest.length) fail("invalid_arguments");
    const key = token.slice(2).replaceAll("-", "_");
    if (!allowed.has(key)) fail("invalid_arguments");
    if (Object.hasOwn(values, key)) fail("duplicate_argument");
    values[key] = rest[++index];
  }
  const required = command === "prepare"
    ? ["trial_dir", "pages_url"]
    : command === "session" ? ["trial_dir", "number"] : ["trial_dir", "aggregate_out"];
  if (required.some(key => !values[key])) fail("invalid_arguments");
  return values;
}

async function readJson(file, code) {
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch {
    fail(code);
  }
}

async function writeJson(file, value) {
  await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
}

function exactPaths(trialDir) {
  return {
    plan: path.join(trialDir, PLAN_FILE),
    state: path.join(trialDir, STATE_FILE),
  };
}

async function replaceJson(file, value) {
  const temporary = `${file}.new`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await rename(temporary, file);
}

export async function assertTrialDirectory(trialDir, {
  repositoryRoot = defaultRepositoryRoot,
  fixtureMode = false,
} = {}) {
  if (!path.isAbsolute(trialDir)) fail("trial_directory_not_absolute");
  const resolved = path.resolve(trialDir);
  const repository = path.resolve(repositoryRoot);
  if (isInside(resolved, repository)) fail("trial_directory_inside_repository");
  for (let cursor = resolved; ; cursor = path.dirname(cursor)) {
    if (existsSync(path.join(cursor, ".git"))) fail("trial_directory_inside_git_worktree");
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
  }
  const lowered = resolved.toLowerCase();
  if (!fixtureMode && (
    lowered.includes(`${path.sep}onedrive${path.sep}`)
    || lowered.includes(`${path.sep}.codex-workspaces${path.sep}`)
    || lowered.includes(`${path.sep}_site${path.sep}`)
    || lowered.includes(`${path.sep}artifacts${path.sep}`)
  )) fail("trial_directory_disallowed_location");
  await mkdir(resolved, { recursive: true });
  const details = await stat(resolved);
  if (!details.isDirectory()) fail("trial_directory_not_directory");
  return resolved;
}

function assertRuntimeSafety({ fixtureMode }) {
  if (fixtureMode) return;
  if (process.env.GITHUB_ACTIONS || process.env.CI) fail("hosted_or_ci_environment");
  const prohibited = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
  ];
  if (prohibited.some(key => process.env[key])) fail("proxy_environment_detected");
}

function validatePlanInput(raw, { fixtureMode }) {
  if (!raw || raw.schema_version !== SCHEMA_VERSION || !isHexDigest(raw.subject_digest)) {
    fail("invalid_plan_contract");
  }
  const pagePath = cleanRelativePath(raw.page_path, "invalid_page_path");
  const catalogPath = cleanRelativePath(raw.catalog_path, "invalid_catalog_path");
  const controllerPath = cleanRelativePath(raw.controller_path, "invalid_controller_path");
  if (!Array.isArray(raw.items) || raw.items.length === 0) fail("empty_plan_population");
  const identities = new Set();
  const items = raw.items.map(item => {
    if (!item || typeof item.identity !== "string" || !item.identity.trim()) {
      fail("invalid_plan_identity");
    }
    if (identities.has(item.identity)) fail("duplicate_plan_identity");
    identities.add(item.identity);
    const source = checkedUrl(item.source_url, { fixtureMode, provider: "source" });
    const control = checkedUrl(item.control_url, { fixtureMode, provider: "control" });
    if (!["official", "community"].includes(item.source_class)) fail("invalid_source_class");
    if (!["single", "multi"].includes(item.face_form)) fail("invalid_face_form");
    if (typeof item.media_type !== "string" || !item.media_type.startsWith("image/")) {
      fail("invalid_media_type");
    }
    return {
      identity: item.identity,
      source_url: source.href,
      control_url: control.href,
      source_class: item.source_class,
      face_form: item.face_form,
      media_type: item.media_type,
      stratum: [source.hostname, item.media_type, item.source_class, item.face_form].join("|"),
    };
  });
  return { pagePath, catalogPath, controllerPath, items };
}

function proportionalQuotas(groups, ceiling) {
  const entries = [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
  const minimum = entries.reduce((sum, [, items]) => sum + Math.min(5, items.length), 0);
  if (minimum > ceiling) fail("stratum_minimum_exceeds_sample_ceiling");
  const quotas = new Map(entries.map(([key, items]) => [key, Math.min(5, items.length)]));
  let remaining = ceiling - minimum;
  while (remaining > 0) {
    const candidates = entries
      .filter(([key, items]) => quotas.get(key) < items.length)
      .sort(([leftKey, leftItems], [rightKey, rightItems]) => {
        const leftRatio = quotas.get(leftKey) / leftItems.length;
        const rightRatio = quotas.get(rightKey) / rightItems.length;
        return leftRatio - rightRatio || leftKey.localeCompare(rightKey);
      });
    if (!candidates.length) break;
    quotas.set(candidates[0][0], quotas.get(candidates[0][0]) + 1);
    remaining -= 1;
  }
  return quotas;
}

export function deterministicSample(raw, { fixtureMode = false } = {}) {
  const { pagePath, catalogPath, controllerPath, items } = validatePlanInput(raw, { fixtureMode });
  const groups = new Map();
  for (const item of items) {
    if (!groups.has(item.stratum)) groups.set(item.stratum, []);
    groups.get(item.stratum).push(item);
  }
  for (const values of groups.values()) {
    values.sort((left, right) => (
      sha256(`${left.identity}|${raw.subject_digest}`)
        .localeCompare(sha256(`${right.identity}|${raw.subject_digest}`))
    ));
  }
  const ceiling = Math.min(MAX_SAMPLE, items.length);
  const quotas = proportionalQuotas(groups, ceiling);
  const selected = [];
  for (const [key, values] of [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    selected.push(...values.slice(0, quotas.get(key)));
  }
  selected.sort((left, right) => (
    sha256(`${left.identity}|${raw.subject_digest}|selected`)
      .localeCompare(sha256(`${right.identity}|${raw.subject_digest}|selected`))
  ));
  const deliberateCount = Math.ceil(selected.length / 2);
  const planned = selected.map((item, index) => {
    const mode = index < deliberateCount ? "deliberate" : "controller";
    const interactionIndex = Number.parseInt(sha256(`${item.identity}|interaction`).slice(0, 8), 16) % 3;
    return {
      ...item,
      mode,
      interaction: mode === "controller" ? ["hover", "focus", "touch"][interactionIndex] : null,
    };
  });
  return {
    schema_version: SCHEMA_VERSION,
    subject_digest: raw.subject_digest,
    page_path: pagePath,
    catalog_path: catalogPath,
    controller_path: controllerPath,
    items: planned,
  };
}

function verifyControllerSource(source) {
  for (const [name, value] of Object.entries(CONTROLLER_CONSTANTS)) {
    const pattern = new RegExp(`const\\s+${name}\\s*=\\s*${value.replace("_", "_")}\\s*;`);
    if (!pattern.test(source)) fail("controller_constant_drift");
  }
}

async function fetchTextInPage(page, pathname) {
  return page.evaluate(async requestedPath => {
    const response = await fetch(requestedPath);
    if (!response.ok) throw new Error("binding_fetch_failed");
    return response.text();
  }, pathname);
}

async function bindPage(browser, {
  pagesUrl,
  pagePath,
  catalogPath,
  controllerPath,
  hasTouch = false,
}) {
  const context = await browser.newContext({
    hasTouch,
    isMobile: hasTouch,
    viewport: hasTouch ? { width: 390, height: 844 } : { width: 1280, height: 800 },
    serviceWorkers: "block",
  });
  if ((await context.cookies()).length) fail("browser_cookie_state_detected");
  const page = await context.newPage();
  const response = await page.goto(pagesUrl, { waitUntil: "domcontentloaded" });
  if (!response || !response.ok()) fail("pages_navigation_failed");
  const current = new URL(page.url());
  const expected = new URL(pagesUrl);
  if (current.origin !== expected.origin || current.pathname !== pagePath) fail("pages_location_drift");
  const [html, catalog, controller] = await Promise.all([
    response.text(),
    fetchTextInPage(page, catalogPath),
    fetchTextInPage(page, controllerPath),
  ]);
  let catalogDocument;
  try {
    catalogDocument = JSON.parse(catalog);
  } catch {
    fail("catalog_not_json");
  }
  const executable = new Set(
    (catalogDocument.formats || [])
      .filter(format => format.state === "executable")
      .map(format => format.id)
  );
  if (!executable.has("standard") || !executable.has("modern")) fail("catalog_subject_drift");
  verifyControllerSource(controller);
  if (!await page.evaluate(() => Boolean(globalThis.P8CardImages?.load))) {
    fail("controller_not_available");
  }
  const serviceWorkerCount = await page.evaluate(async () => (
    "serviceWorker" in navigator ? (await navigator.serviceWorker.getRegistrations()).length : 0
  ));
  if (serviceWorkerCount) fail("service_worker_detected");
  return {
    context,
    page,
    bindings: {
      html_sha256: sha256(html),
      catalog_sha256: sha256(catalog),
      controller_sha256: sha256(controller),
    },
  };
}

function sameBindings(left, right) {
  return stableJson(left) === stableJson(right);
}

function emptyProviderAggregate() {
  return {
    logical_loads: 0,
    physical_starts: 0,
    decoded: 0,
    failed: 0,
    timed_out: 0,
    http_classes: {},
    redirect_classes: {},
    final_host_classes: {},
    response_body_bytes: [],
    decode_ms: [],
  };
}

function emptySessionAggregate(number, startedAt) {
  return {
    number,
    started_at: startedAt,
    completed_at: null,
    source: emptyProviderAggregate(),
    control: emptyProviderAggregate(),
    fallback_attempted: 0,
    fallback_decoded: 0,
    cache: { avoided: 0, reduced: 0, unchanged: 0, not_applicable_failed: 0, unavailable: 0 },
    interactions: { deliberate: 0, hover: 0, focus: 0, touch: 0 },
    strata: {},
  };
}

function incrementCounter(object, key) {
  object[key] = (object[key] || 0) + 1;
}

function httpClass(status) {
  if (!Number.isInteger(status) || status <= 0) return "transport";
  return `${Math.floor(status / 100)}xx`;
}

function attachImageObservation(page, allowedHosts) {
  const requests = [];
  const pending = [];
  const byRequest = new Map();
  let unsafeRedirect = false;
  const onRequest = request => {
    if (request.resourceType() !== "image") return;
    const parsed = new URL(request.url());
    if (!allowedHosts.has(parsed.hostname)) unsafeRedirect = true;
    const entry = { request, status: 0, contentType: "", bytes: null };
    requests.push(entry);
    byRequest.set(request, entry);
  };
  const onResponse = response => {
    const entry = byRequest.get(response.request());
    if (!entry) return;
    entry.status = response.status();
    entry.contentType = response.headers()["content-type"] || "";
  };
  const onFinished = request => {
    const entry = byRequest.get(request);
    if (!entry) return;
    pending.push(request.sizes().then(sizes => {
      entry.bytes = sizes.responseBodySize;
    }).catch(() => {
      entry.bytes = null;
    }));
  };
  page.on("request", onRequest);
  page.on("response", onResponse);
  page.on("requestfinished", onFinished);
  page.on("requestfailed", onFinished);
  return async () => {
    page.off("request", onRequest);
    page.off("response", onResponse);
    page.off("requestfinished", onFinished);
    page.off("requestfailed", onFinished);
    await Promise.allSettled(pending);
    if (unsafeRedirect) fail("unsafe_redirect_host");
    return requests;
  };
}

async function deliberateLoad(page, url) {
  return page.evaluate(async sourceUrl => {
    const image = document.createElement("img");
    image.alt = "";
    image.setAttribute("data-stage-c-current", "");
    document.body.append(image);
    const started = performance.now();
    try {
      image.src = sourceUrl;
      await image.decode();
      return {
        decoded: image.naturalWidth > 0 && image.naturalHeight > 0,
        decodeMs: performance.now() - started,
      };
    } catch {
      return { decoded: false, decodeMs: performance.now() - started };
    } finally {
      image.remove();
    }
  }, url);
}

async function controllerLoad(page, url, interaction) {
  await page.evaluate(({ sourceUrl, interactionName }) => {
    document.querySelector("[data-stage-c-current]")?.remove();
    const link = document.createElement("a");
    link.href = "#";
    link.textContent = "trial";
    link.dataset.cardImage = sourceUrl;
    link.dataset.cardName = "trial";
    link.dataset.stageCCurrent = interactionName;
    document.body.append(link);
  }, { sourceUrl: url, interactionName: interaction });
  const link = page.locator("[data-stage-c-current]");
  const started = Date.now();
  if (interaction === "hover") {
    await link.dispatchEvent("mouseover", { relatedTarget: null });
  } else if (interaction === "focus") {
    await link.evaluate(node => node.focus());
  } else {
    await link.tap({ timeout: 5_000 });
  }
  const frame = interaction === "touch"
    ? page.locator("#card-preview-modal .card-image-frame")
    : page.locator("#card-preview .card-image-frame");
  await frame.waitFor({ state: "attached" });
  await page.waitForFunction(({ touch }) => {
    const selector = touch
      ? "#card-preview-modal .card-image-frame"
      : "#card-preview .card-image-frame";
    const node = document.querySelector(selector);
    return node?.classList.contains("is-loaded") || node?.classList.contains("is-error");
  }, { touch: interaction === "touch" }, { timeout: 20_000 });
  const decoded = await frame.evaluate(node => {
    if (!node.classList.contains("is-loaded")) return false;
    const image = node.querySelector("img");
    return image?.decode().then(
      () => image.naturalWidth > 0 && image.naturalHeight > 0,
      () => false
    );
  });
  await page.evaluate(interactionName => {
    globalThis.P8CardImages.cancelQueued("desktop-preview");
    document.querySelector("[data-stage-c-current]")?.remove();
    if (interactionName === "touch") {
      document.querySelector("[data-card-preview-close]")?.click();
    }
  }, interaction);
  return { decoded, decodeMs: Date.now() - started };
}

async function measuredLoad(page, {
  url,
  mode,
  interaction,
  allowedHosts,
  expectedHost,
  pace = async () => {},
}) {
  await pace(mode);
  const finishObservation = attachImageObservation(page, allowedHosts);
  let result;
  try {
    result = mode === "deliberate"
      ? await deliberateLoad(page, url)
      : await controllerLoad(page, url, interaction);
  } catch {
    result = { decoded: false, decodeMs: 20_000, timedOut: true };
  }
  await page.waitForTimeout(25);
  const requests = await finishObservation();
  const final = requests.at(-1);
  if (final?.status >= 200 && final.status < 300
      && !final.contentType.toLowerCase().startsWith("image/")) {
    fail("non_image_payload");
  }
  const finalHost = final ? new URL(final.request.url()).hostname : null;
  const redirectHosts = requests.map(request => new URL(request.request.url()).hostname);
  const redirectClass = redirectHosts.length <= 1
    ? "none"
    : new Set(redirectHosts).size === 1 ? "same_host" : "cross_host";
  return {
    decoded: Boolean(result.decoded),
    decodeMs: Math.round(result.decodeMs),
    timedOut: Boolean(result.timedOut),
    physicalStarts: requests.length,
    status: final?.status || 0,
    bytes: requests.reduce((sum, request) => sum + (request.bytes || 0), 0),
    redirectClass,
    finalHostClass: finalHost === null ? "none" : finalHost === expectedHost ? "expected" : "allowed_redirect",
  };
}

function applyOutcome(aggregate, provider, outcome) {
  const target = aggregate[provider];
  target.logical_loads += 1;
  target.physical_starts += outcome.physicalStarts;
  if (target.logical_loads > MAX_LOGICAL) fail("logical_budget_exceeded");
  if (target.physical_starts > MAX_PHYSICAL) fail("physical_budget_exceeded");
  incrementCounter(target.http_classes, httpClass(outcome.status));
  if (outcome.decoded) target.decoded += 1;
  else target.failed += 1;
  if (outcome.timedOut) target.timed_out += 1;
  incrementCounter(target.redirect_classes, outcome.redirectClass);
  incrementCounter(target.final_host_classes, outcome.finalHostClass);
  if (Number.isFinite(outcome.bytes)) target.response_body_bytes.push(outcome.bytes);
  if (outcome.decoded) target.decode_ms.push(outcome.decodeMs);
}

function classifyCache(cold, warm) {
  if (!cold.decoded && !warm.decoded) return "not_applicable_failed";
  if (!warm.decoded) return "unavailable";
  if (warm.physicalStarts === 0 || warm.bytes === 0) return "avoided";
  if (cold.bytes > 0 && warm.bytes <= cold.bytes * 0.1) return "reduced";
  if (cold.bytes > 0) return "unchanged";
  return "unavailable";
}

function createPacer(fixtureMode) {
  let lastDeliberateStart = 0;
  return async mode => {
    if (mode !== "deliberate") return;
    const minimumInterval = fixtureMode ? 0 : 10_000;
    const remaining = minimumInterval - (Date.now() - lastDeliberateStart);
    if (remaining > 0) await new Promise(resolve => setTimeout(resolve, remaining));
    lastDeliberateStart = Date.now();
  };
}

async function executeItem(page, item, aggregate, allowedHosts, pace) {
  const interaction = item.mode === "deliberate" ? "deliberate" : item.interaction;
  incrementCounter(aggregate.interactions, interaction);
  incrementCounter(aggregate.strata, item.stratum);
  const sourceCold = await measuredLoad(page, {
    url: item.source_url,
    mode: item.mode,
    interaction: item.interaction,
    allowedHosts,
    expectedHost: new URL(item.source_url).hostname,
    pace,
  });
  applyOutcome(aggregate, "source", sourceCold);
  const controlCold = await measuredLoad(page, {
    url: item.control_url,
    mode: item.mode,
    interaction: item.interaction,
    allowedHosts,
    expectedHost: new URL(item.control_url).hostname,
    pace,
  });
  applyOutcome(aggregate, "control", controlCold);
  if (!sourceCold.decoded) {
    aggregate.fallback_attempted += 1;
    if (controlCold.decoded) aggregate.fallback_decoded += 1;
  }
  const sourceWarm = await measuredLoad(page, {
    url: item.source_url,
    mode: item.mode,
    interaction: item.interaction,
    allowedHosts,
    expectedHost: new URL(item.source_url).hostname,
    pace,
  });
  applyOutcome(aggregate, "source", sourceWarm);
  const controlWarm = await measuredLoad(page, {
    url: item.control_url,
    mode: item.mode,
    interaction: item.interaction,
    allowedHosts,
    expectedHost: new URL(item.control_url).hostname,
    pace,
  });
  applyOutcome(aggregate, "control", controlWarm);
  incrementCounter(aggregate.cache, classifyCache(sourceCold, sourceWarm));
  incrementCounter(aggregate.cache, classifyCache(controlCold, controlWarm));
}

function percentile(values, fraction) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * fraction) - 1)];
}

function summarizeProvider(provider) {
  return {
    logical_loads: provider.logical_loads,
    physical_starts: provider.physical_starts,
    decoded: provider.decoded,
    failed: provider.failed,
    timed_out: provider.timed_out,
    http_classes: provider.http_classes,
    redirect_classes: provider.redirect_classes,
    final_host_classes: provider.final_host_classes,
    response_body_bytes: {
      median: percentile(provider.response_body_bytes, 0.5),
      p95: percentile(provider.response_body_bytes, 0.95),
    },
    decode_ms: {
      median: percentile(provider.decode_ms, 0.5),
      p95: percentile(provider.decode_ms, 0.95),
    },
  };
}

function safeSessionAggregate(raw) {
  return {
    number: raw.number,
    started_at: raw.started_at,
    completed_at: raw.completed_at,
    source: summarizeProvider(raw.source),
    control: summarizeProvider(raw.control),
    fallback_attempted: raw.fallback_attempted,
    fallback_decoded: raw.fallback_decoded,
    cache: raw.cache,
    interactions: raw.interactions,
    strata: raw.strata,
  };
}

export function assertCumulativeBudget(existingSessions, current) {
  for (const provider of ["source", "control"]) {
    const logical = existingSessions.reduce(
      (sum, session) => sum + session[provider].logical_loads,
      current[provider].logical_loads
    );
    const physical = existingSessions.reduce(
      (sum, session) => sum + session[provider].physical_starts,
      current[provider].physical_starts
    );
    if (logical > MAX_LOGICAL) fail("logical_budget_exceeded");
    if (physical > MAX_PHYSICAL) fail("physical_budget_exceeded");
  }
}

async function cleanupExactPlan(trialDir) {
  if (!trialDir || !path.isAbsolute(trialDir)) return;
  await rm(path.join(trialDir, PLAN_FILE), { force: true });
}

export async function prepareTrial({
  trialDir,
  pagesUrl,
  planInput,
  fixtureMode = false,
  repositoryRoot = defaultRepositoryRoot,
} = {}) {
  assertRuntimeSafety({ fixtureMode });
  const directory = await assertTrialDirectory(trialDir, { repositoryRoot, fixtureMode });
  const paths = exactPaths(directory);
  if (existsSync(paths.plan) || existsSync(paths.state)) fail("trial_state_already_exists");
  const inputPath = planInput || path.join(directory, "plan-input.json");
  if (!path.isAbsolute(inputPath) || !isInside(inputPath, directory)) {
    fail("plan_input_must_be_inside_trial_directory");
  }
  try {
    const raw = await readJson(inputPath, "plan_input_not_json");
    const plan = deterministicSample(raw, { fixtureMode });
    const pageUrl = new URL(pagesUrl);
    if (fixtureMode) {
      if (!isLoopback(pageUrl.hostname)) fail("fixture_pages_not_loopback");
    } else if (pageUrl.protocol !== "https:") fail("pages_not_https");
    if (pageUrl.pathname !== plan.page_path) fail("pages_path_mismatch");
    const browser = await chromium.launch({ headless: true });
    let bound;
    const browserVersion = browser.version();
    try {
      bound = await bindPage(browser, {
        pagesUrl,
        pagePath: plan.page_path,
        catalogPath: plan.catalog_path,
        controllerPath: plan.controller_path,
      });
      await bound.context.close();
    } finally {
      await browser.close();
    }
    const planDigest = sha256(stableJson(plan));
    await writeJson(paths.plan, plan);
    await rm(inputPath, { force: true });
    const state = {
      schema_version: SCHEMA_VERSION,
      status: "prepared",
      prepared_at: new Date().toISOString(),
      trial_directory_digest: sha256(directory),
      pages_origin: pageUrl.origin,
      page_path: plan.page_path,
      plan_digest: planDigest,
      sample_size: plan.items.length,
      subject_digest: plan.subject_digest,
      bindings: bound.bindings,
      browser_version: browserVersion,
      playwright_version: playwrightVersion,
      sessions: [],
    };
    await writeJson(paths.state, state);
    return { plan_digest: planDigest, sample_size: plan.items.length, bindings: bound.bindings };
  } catch (error) {
    await rm(inputPath, { force: true });
    await cleanupExactPlan(directory);
    throw error;
  }
}

async function runTrialSessionInner({
  trialDir,
  validatedDirectory,
  number,
  fixtureMode = false,
  repositoryRoot = defaultRepositoryRoot,
  onProgress = () => {},
} = {}) {
  assertRuntimeSafety({ fixtureMode });
  const directory = validatedDirectory;
  const paths = exactPaths(directory);
  const state = await readJson(paths.state, "trial_state_not_json");
  const plan = await readJson(paths.plan, "exact_plan_not_json");
  if (Number(number) !== 1) fail("invalid_session_number");
  const sessionNumber = Number(number);
  if (sessionNumber !== state.sessions.length + 1) fail("session_order_invalid");
  if (state.playwright_version !== playwrightVersion) fail("playwright_version_drift");
  if (sha256(stableJson(plan)) !== state.plan_digest) fail("exact_plan_digest_drift");
  const startedAt = new Date().toISOString();
  const aggregate = emptySessionAggregate(sessionNumber, startedAt);
  const pace = createPacer(fixtureMode);
  const pageUrl = `${state.pages_origin}${state.page_path}`;
  const allowedHosts = new Set([
    new URL(pageUrl).hostname,
    ...plan.items.flatMap(item => [new URL(item.source_url).hostname, new URL(item.control_url).hostname]),
  ]);
  const browser = await chromium.launch({ headless: true });
  try {
    if (browser.version() !== state.browser_version) fail("browser_version_drift");
    const groups = [
      { hasTouch: false, items: plan.items.filter(item => item.interaction !== "touch") },
      { hasTouch: true, items: plan.items.filter(item => item.interaction === "touch") },
    ];
    let completedItems = 0;
    for (const group of groups) {
      if (!group.items.length) continue;
      const bound = await bindPage(browser, {
        pagesUrl: pageUrl,
        pagePath: plan.page_path,
        catalogPath: plan.catalog_path,
        controllerPath: plan.controller_path,
        hasTouch: group.hasTouch,
      });
      try {
        if (!sameBindings(bound.bindings, state.bindings)) fail("pages_binding_drift");
        for (const item of group.items) {
          onProgress({
            session: sessionNumber,
            completed: completedItems,
            total: plan.items.length,
            mode: item.mode,
            interaction: item.interaction,
          });
          await executeItem(bound.page, item, aggregate, allowedHosts, pace);
          completedItems += 1;
        }
      } finally {
        await bound.context.close();
      }
    }
  } catch (error) {
    await cleanupExactPlan(directory);
    throw error;
  } finally {
    await browser.close();
  }
  if (aggregate.cache.unavailable) {
    await cleanupExactPlan(directory);
    fail("cache_observation_unavailable");
  }
  assertCumulativeBudget(state.sessions, aggregate);
  aggregate.completed_at = new Date().toISOString();
  state.sessions.push(safeSessionAggregate(aggregate));
  state.status = "session_complete";
  await replaceJson(paths.state, state);
  return state.sessions.at(-1);
}

export async function runTrialSession(options = {}) {
  let directory;
  try {
    directory = await assertTrialDirectory(options.trialDir, {
      repositoryRoot: options.repositoryRoot || defaultRepositoryRoot,
      fixtureMode: Boolean(options.fixtureMode),
    });
    return await runTrialSessionInner({ ...options, validatedDirectory: directory });
  } catch (error) {
    if (directory) await cleanupExactPlan(directory);
    throw error;
  }
}

function assertAggregateRedacted(aggregate, plan) {
  const serialized = JSON.stringify(aggregate);
  for (const item of plan.items) {
    const forbidden = [item.identity, item.source_url, item.control_url];
    if (forbidden.some(value => serialized.includes(value))) fail("aggregate_contains_exact_identity");
  }
}

async function finalizeTrialInner({
  trialDir,
  validatedDirectory,
  aggregateOut,
  fixtureMode = false,
  repositoryRoot = defaultRepositoryRoot,
} = {}) {
  const directory = validatedDirectory;
  const paths = exactPaths(directory);
  const state = await readJson(paths.state, "trial_state_not_json");
  const plan = await readJson(paths.plan, "exact_plan_not_json");
  if (!["session_complete", "session_1_complete"].includes(state.status)
      || state.sessions.length !== 1) {
    await cleanupExactPlan(directory);
    fail("trial_not_complete");
  }
  if (!aggregateOut || !path.isAbsolute(aggregateOut) || isInside(aggregateOut, repositoryRoot)) {
    fail("aggregate_output_not_external");
  }
  const aggregate = {
    schema_version: SCHEMA_VERSION,
    result: "complete",
    subject_digest: state.subject_digest,
    plan_digest: state.plan_digest,
    sample_size: state.sample_size,
    bindings: state.bindings,
    browser_version: state.browser_version,
    playwright_version: state.playwright_version,
    sessions: state.sessions,
  };
  assertAggregateRedacted(aggregate, plan);
  await writeFile(aggregateOut, `${JSON.stringify(aggregate, null, 2)}\n`, "utf8");
  await cleanupExactPlan(directory);
  state.status = "finalized";
  state.finalized_at = new Date().toISOString();
  await replaceJson(paths.state, state);
  return aggregate;
}

export async function finalizeTrial(options = {}) {
  let directory;
  try {
    directory = await assertTrialDirectory(options.trialDir, {
      repositoryRoot: options.repositoryRoot || defaultRepositoryRoot,
      fixtureMode: Boolean(options.fixtureMode),
    });
    return await finalizeTrialInner({ ...options, validatedDirectory: directory });
  } catch (error) {
    if (directory) await cleanupExactPlan(directory);
    throw error;
  }
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  try {
    if (args.command === "prepare") {
      const result = await prepareTrial({
        trialDir: args.trial_dir,
        pagesUrl: args.pages_url,
        planInput: args.plan_input,
        fixtureMode: args.fixtureMode,
      });
      process.stdout.write(`${JSON.stringify(result)}\n`);
    } else if (args.command === "session") {
      const result = await runTrialSession({
        trialDir: args.trial_dir,
        number: Number(args.number),
        fixtureMode: args.fixtureMode,
      });
      process.stdout.write(`${JSON.stringify(result)}\n`);
    } else {
      const result = await finalizeTrial({
        trialDir: args.trial_dir,
        aggregateOut: args.aggregate_out,
        fixtureMode: args.fixtureMode,
      });
      process.stdout.write(`${JSON.stringify({ result: result.result })}\n`);
    }
  } catch (error) {
    const trialDir = args.trial_dir;
    if (trialDir && path.isAbsolute(trialDir) && error instanceof StageCContractError) {
      await cleanupExactPlan(trialDir);
    }
    const code = error instanceof StageCContractError ? error.code : "unexpected_runner_error";
    process.stderr.write(`${JSON.stringify({ result: "inconclusive", stop: code })}\n`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(scriptPath)) {
  await main();
}
