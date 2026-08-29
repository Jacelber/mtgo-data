"use strict";

const { createHash } = require("node:crypto");
const http = require("node:http");
const { mkdtemp, readFile, rm, writeFile } = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const { expect, test } = require("@playwright/test");

test.use({ trace: "off", video: "off", screenshot: "off" });

const root = path.resolve(__dirname, "../..");
const fixtureRoot = path.join(root, "tests/fixtures/card-localization-stage-c");
const controllerPath = path.join(root, "assets/js/phase8/app-card-preview.js");
const runnerUrl = pathToFileURL(
  path.join(root, "scripts/run_card_localization_stage_c_trial.mjs")
).href;

function digest(value) {
  return createHash("sha256").update(value).digest("hex");
}

function svg(label) {
  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="28"><title>${label}</title><rect width="20" height="28" fill="#345"/></svg>`
  );
}

async function fixtureServer({ failSource = false } = {}) {
  const html = await readFile(path.join(fixtureRoot, "index.html"));
  const catalog = await readFile(path.join(fixtureRoot, "catalog.json"));
  let controller = await readFile(controllerPath);
  const slowRequests = [];
  const server = http.createServer((request, response) => {
    const pathname = new URL(request.url, "http://127.0.0.1").pathname;
    if (pathname === "/index.html") {
      response.writeHead(200, { "Content-Type": "text/html", "Content-Length": html.length });
      response.end(html);
      return;
    }
    if (pathname === "/stats/catalog.json") {
      response.writeHead(200, { "Content-Type": "application/json", "Content-Length": catalog.length });
      response.end(catalog);
      return;
    }
    if (pathname === "/assets/js/phase8/app-card-preview.js") {
      response.writeHead(200, { "Content-Type": "text/javascript", "Content-Length": controller.length });
      response.end(controller);
      return;
    }
    if (pathname.startsWith("/slow/")) {
      slowRequests.push(pathname);
      const payload = svg("slow fixture");
      setTimeout(() => {
        response.writeHead(200, {
          "Cache-Control": "no-store",
          "Content-Length": payload.length,
          "Content-Type": "image/svg+xml",
        });
        response.end(payload);
      }, 300);
      return;
    }
    if (failSource && pathname.startsWith("/source/")) {
      const payload = Buffer.from("synthetic failure");
      response.writeHead(503, {
        "Content-Length": payload.length,
        "Content-Type": "text/plain",
      });
      response.end(payload);
      return;
    }
    if (pathname.startsWith("/source/") || pathname.startsWith("/control/")) {
      const payload = svg("fixture");
      response.writeHead(200, {
        "Cache-Control": "public, max-age=3600, immutable",
        "Content-Length": payload.length,
        "Content-Type": "image/svg+xml",
      });
      response.end(payload);
      return;
    }
    response.writeHead(404).end();
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  return {
    origin: `http://127.0.0.1:${address.port}`,
    driftController: () => {
      controller = Buffer.concat([controller, Buffer.from("\n// synthetic drift\n")]);
    },
    slowRequests,
    close: () => new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())),
  };
}

function plan(origin, count = 10) {
  return {
    schema_version: "1.0.0",
    subject_digest: digest("synthetic-subject"),
    page_path: "/index.html",
    catalog_path: "/stats/catalog.json",
    controller_path: "/assets/js/phase8/app-card-preview.js",
    items: Array.from({ length: count }, (_, index) => ({
      identity: `fixture-identity-${index}`,
      source_url: `${origin}/source/${index}.svg`,
      control_url: `${origin}/control/${index}.svg`,
      source_class: "community",
      face_form: index < 5 ? "single" : "multi",
      media_type: "image/svg+xml",
    })),
  };
}

test("deterministic sampling covers every synthetic stratum without editorial order", async () => {
  const { deterministicSample } = await import(runnerUrl);
  const input = plan("http://127.0.0.1:9137", 16);
  const first = deterministicSample(input, { fixtureMode: true });
  const second = deterministicSample({ ...input, items: [...input.items].reverse() }, { fixtureMode: true });
  expect(first).toEqual(second);
  expect(new Set(first.items.map(item => item.stratum)).size).toBe(2);
  expect(first.items).toHaveLength(16);
  expect(first.items.filter(item => item.mode === "deliberate")).toHaveLength(8);
  expect(first.items.filter(item => item.mode === "controller")).toHaveLength(8);
});

test("command parsing and the two-session budget fail closed", async () => {
  const {
    assertCumulativeBudget,
    parseArguments,
    StageCContractError,
  } = await import(runnerUrl);
  expect(parseArguments([
    "session", "--trial-dir", "C:/temporary", "--number", "2",
  ])).toEqual(expect.objectContaining({
    command: "session",
    trial_dir: "C:/temporary",
    number: "2",
  }));
  expect(() => parseArguments(["session", "--number", "1", "--number", "2"]))
    .toThrow(expect.objectContaining({ code: "duplicate_argument" }));
  expect(() => parseArguments(["prepare", "--trial-dir", "C:/temporary"]))
    .toThrow(expect.objectContaining({ code: "invalid_arguments" }));
  expect(() => parseArguments(["finalize", "--trial-dir", "C:/temporary", "--extra", "x"]))
    .toThrow(expect.objectContaining({ code: "invalid_arguments" }));
  const provider = (logical, physical) => ({ logical_loads: logical, physical_starts: physical });
  expect(() => assertCumulativeBudget([], {
    source: provider(401, 1),
    control: provider(1, 1),
  })).toThrow(expect.objectContaining({
    name: StageCContractError.name,
    code: "logical_budget_exceeded",
  }));
  expect(() => assertCumulativeBudget([], {
    source: provider(1, 801),
    control: provider(1, 1),
  })).toThrow(expect.objectContaining({ code: "physical_budget_exceeded" }));
});

test("the bound controller abandons hover UI and cancels a queued image", async ({ page }) => {
  const server = await fixtureServer();
  try {
    await page.goto(`${server.origin}/index.html`);
    const result = await page.evaluate(async origin => {
      const first = globalThis.P8CardImages.load(`${origin}/slow/active.svg`, {
        owner: "active",
      });
      const queued = globalThis.P8CardImages.load(`${origin}/slow/cancelled.svg`, {
        owner: "queued",
      }).then(() => "loaded", error => error.code);
      globalThis.P8CardImages.cancelQueued("queued");
      const queuedResult = await queued;
      await first;

      const link = document.createElement("a");
      link.href = "#";
      link.dataset.cardImage = `${origin}/slow/hover.svg`;
      link.dataset.cardName = "fixture";
      document.body.append(link);
      link.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
      link.dispatchEvent(new MouseEvent("mouseout", { bubbles: true }));
      const hiddenAfterAbandonment = document.querySelector("#card-preview").hidden;
      link.remove();
      return { queuedResult, hiddenAfterAbandonment };
    }, server.origin);
    expect(result).toEqual({ queuedResult: "cancelled", hiddenAfterAbandonment: true });
    await expect.poll(() => server.slowRequests).toEqual([
      "/slow/active.svg",
      "/slow/hover.svg",
    ]);
  } finally {
    await server.close();
  }
});

test("the loopback runner completes two sessions, redacts the aggregate, and deletes the exact plan", async () => {
  test.setTimeout(120_000);
  const {
    finalizeTrial,
    prepareTrial,
    runTrialSession,
  } = await import(runnerUrl);
  const server = await fixtureServer();
  const trialDir = await mkdtemp(path.join(os.tmpdir(), "stage-c-runner-"));
  const planInput = path.join(trialDir, "plan-input.json");
  const aggregateOut = path.join(os.tmpdir(), `stage-c-aggregate-${Date.now()}.json`);
  const input = plan(server.origin);
  await writeFile(planInput, JSON.stringify(input));
  try {
    const prepared = await prepareTrial({
      trialDir,
      pagesUrl: `${server.origin}/index.html`,
      planInput,
      fixtureMode: true,
      repositoryRoot: root,
    });
    expect(prepared.sample_size).toBe(10);
    await runTrialSession({
      trialDir,
      number: 1,
      fixtureMode: true,
      minimumGapMs: 0,
      repositoryRoot: root,
    });
    await runTrialSession({
      trialDir,
      number: 2,
      fixtureMode: true,
      minimumGapMs: 0,
      repositoryRoot: root,
    });
    const aggregate = await finalizeTrial({
      trialDir,
      aggregateOut,
      fixtureMode: true,
      repositoryRoot: root,
    });
    expect(aggregate.result).toBe("complete");
    expect(aggregate.sessions).toHaveLength(2);
    expect(aggregate.sessions[0].source.logical_loads).toBe(20);
    expect(aggregate.sessions[0].control.logical_loads).toBe(20);
    expect(aggregate.sessions[0].cache.unavailable).toBe(0);
    expect(aggregate.sessions[0].source.redirect_classes.none).toBe(20);
    expect(aggregate.sessions[0].source.final_host_classes.expected).toBe(10);
    expect(aggregate.sessions[0].source.final_host_classes.none).toBe(10);
    expect(aggregate.sessions[0].interactions).toEqual(expect.objectContaining({
      deliberate: 5,
      hover: 1,
      focus: 2,
      touch: 2,
    }));
    const serialized = await readFile(aggregateOut, "utf8");
    for (const item of input.items) {
      expect(serialized).not.toContain(item.identity);
      expect(serialized).not.toContain(item.source_url);
      expect(serialized).not.toContain(item.control_url);
    }
    await expect(readFile(path.join(trialDir, "exact-plan.json"), "utf8")).rejects.toThrow();
  } finally {
    await server.close();
    await rm(trialDir, { recursive: true, force: true });
    await rm(aggregateOut, { force: true });
  }
});

test("a served controller drift stops the session and removes the exact plan", async () => {
  const {
    prepareTrial,
    runTrialSession,
  } = await import(runnerUrl);
  const server = await fixtureServer();
  const trialDir = await mkdtemp(path.join(os.tmpdir(), "stage-c-drift-"));
  const planInput = path.join(trialDir, "plan-input.json");
  await writeFile(planInput, JSON.stringify(plan(server.origin)));
  try {
    await prepareTrial({
      trialDir,
      pagesUrl: `${server.origin}/index.html`,
      planInput,
      fixtureMode: true,
      repositoryRoot: root,
    });
    server.driftController();
    await expect(runTrialSession({
      trialDir,
      number: 1,
      fixtureMode: true,
      repositoryRoot: root,
    })).rejects.toEqual(expect.objectContaining({ code: "pages_binding_drift" }));
    await expect(readFile(path.join(trialDir, "exact-plan.json"), "utf8")).rejects.toThrow();
  } finally {
    await server.close();
    await rm(trialDir, { recursive: true, force: true });
  }
});

test("an early second session stops and removes the exact plan", async () => {
  test.setTimeout(60_000);
  const {
    prepareTrial,
    runTrialSession,
  } = await import(runnerUrl);
  const server = await fixtureServer();
  const trialDir = await mkdtemp(path.join(os.tmpdir(), "stage-c-gap-"));
  const planInput = path.join(trialDir, "plan-input.json");
  await writeFile(planInput, JSON.stringify(plan(server.origin, 2)));
  try {
    await prepareTrial({
      trialDir,
      pagesUrl: `${server.origin}/index.html`,
      planInput,
      fixtureMode: true,
      repositoryRoot: root,
    });
    await runTrialSession({
      trialDir,
      number: 1,
      fixtureMode: true,
      minimumGapMs: 0,
      repositoryRoot: root,
    });
    await expect(runTrialSession({
      trialDir,
      number: 2,
      fixtureMode: true,
      minimumGapMs: 60_000,
      repositoryRoot: root,
    })).rejects.toEqual(expect.objectContaining({ code: "session_gap_too_short" }));
    await expect(readFile(path.join(trialDir, "exact-plan.json"), "utf8")).rejects.toThrow();
  } finally {
    await server.close();
    await rm(trialDir, { recursive: true, force: true });
  }
});

test("a source HTTP failure is counted and its control fallback decodes", async () => {
  test.setTimeout(60_000);
  const {
    prepareTrial,
    runTrialSession,
  } = await import(runnerUrl);
  const server = await fixtureServer({ failSource: true });
  const trialDir = await mkdtemp(path.join(os.tmpdir(), "stage-c-fallback-"));
  const planInput = path.join(trialDir, "plan-input.json");
  await writeFile(planInput, JSON.stringify(plan(server.origin, 2)));
  try {
    await prepareTrial({
      trialDir,
      pagesUrl: `${server.origin}/index.html`,
      planInput,
      fixtureMode: true,
      repositoryRoot: root,
    });
    const aggregate = await runTrialSession({
      trialDir,
      number: 1,
      fixtureMode: true,
      minimumGapMs: 0,
      repositoryRoot: root,
    });
    expect(aggregate.source.http_classes["5xx"]).toBeGreaterThan(0);
    expect(aggregate.fallback_attempted).toBe(2);
    expect(aggregate.fallback_decoded).toBe(2);
    expect(aggregate.cache.not_applicable_failed).toBe(2);
    expect(aggregate.cache.unavailable).toBe(0);
  } finally {
    await server.close();
    await rm(trialDir, { recursive: true, force: true });
  }
});

test("a preparation stop removes its external exact input", async () => {
  const { prepareTrial } = await import(runnerUrl);
  const trialDir = await mkdtemp(path.join(os.tmpdir(), "stage-c-prepare-stop-"));
  const planInput = path.join(trialDir, "plan-input.json");
  const input = plan("http://127.0.0.1:9137");
  await writeFile(planInput, JSON.stringify({ ...input, page_path: "/different.html" }));
  try {
    await expect(prepareTrial({
      trialDir,
      pagesUrl: "http://127.0.0.1:9137/index.html",
      planInput,
      fixtureMode: true,
      repositoryRoot: root,
    })).rejects.toEqual(expect.objectContaining({ code: "pages_path_mismatch" }));
    await expect(readFile(planInput, "utf8")).rejects.toThrow();
  } finally {
    await rm(trialDir, { recursive: true, force: true });
  }
});

test("the runner rejects a trial directory inside the repository", async () => {
  const { assertTrialDirectory, StageCContractError } = await import(runnerUrl);
  await expect(assertTrialDirectory(path.join(root, "temporary-trial"), {
    fixtureMode: true,
    repositoryRoot: root,
  })).rejects.toEqual(expect.objectContaining({
    name: StageCContractError.name,
    code: "trial_directory_inside_repository",
  }));
});
