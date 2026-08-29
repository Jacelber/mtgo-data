"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const runtimeSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/runtime.js"),
  "utf8"
);
const mtgoControllerSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/mtgo-controller.js"),
  "utf8"
);

function runtimeWith(fetchImpl) {
  const context = {
    AbortController,
    DOMException,
    TextEncoder,
    clearTimeout,
    document: { documentElement: { dataset: { statsBase: "./" } } },
    fetch: fetchImpl,
    setTimeout,
  };
  context.globalThis = context;
  vm.runInNewContext(runtimeSource, context);
  return context.P8Runtime;
}

function response(value, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async text() {
      return JSON.stringify(value);
    },
  };
}

function mtgoControllerWith(documents) {
  const runtime = runtimeWith(async url => (
    documents.has(url)
      ? response(documents.get(url))
      : response({ missing: url }, { status: 404 })
  ));
  const context = { P8Runtime: runtime };
  context.globalThis = context;
  vm.runInNewContext(mtgoControllerSource, context);
  return context.P8MtgoController;
}

function landingDocuments({ companionWeek = "2026-W33", rangeFormat = "standard" } = {}) {
  const period = companionWeek === "2026-W33"
    ? { start: "2026-08-10", end: "2026-08-16" }
    : { start: "2026-08-17", end: "2026-08-23" };
  return new Map([
    ["./stats/standard/mtgo/landing/current.json", {
      format: "standard",
      week: { id: "2026-W33", start: "2026-08-10", end: "2026-08-16" },
    }],
    ["./stats/standard/mtgo/meta.json", { format: "standard" }],
    ["./stats/standard/mtgo/range_1w.json", { format: rangeFormat, period, total_decks: 70 }],
    ["./stats/standard/mtgo/completeness/1w.json", { format: "standard", period }],
    ["./stats/standard/mtgo/landing/features/index.json", {
      format: "standard",
      weeks: [{ week: "2026-W33", file: "2026-W33.json", feature_count: 1 }],
    }],
    ["./stats/standard/mtgo/landing/features/2026-W33.json", {
      format: "standard",
      week: { id: "2026-W33" },
      features: { items: [] },
    }],
    ["./stats/standard/mtgo/decks_1w.json", { format: "standard", decks: [] }],
    ["./stats/standard/mtgo/decks_4w.json", { format: "standard", decks: [] }],
  ]);
}

function cardImageCacheManifest({ selectedWeeks = ["2026-W33"] } = {}) {
  return {
    schema_version: "1.1.0",
    product: "mtgo-landing-card-image-cache",
    public_prefix: "assets/card-cache/v1",
    window_size_weeks: 4,
    formats: [{ format: "standard", selected_weeks: selectedWeeks }],
    cards: [{
      cache_source: "generated",
      name: "Cached Card",
      local_path: "assets/card-cache/v1/images/11111111-1111-4111-8111-111111111111.jpg",
      uses: [{ format: "standard", weeks: ["2026-W33"] }],
    }],
  };
}

test("failed requests are evicted and a manual retry starts a new fetch", async () => {
  let calls = 0;
  const runtime = runtimeWith(async () => {
    calls += 1;
    if (calls === 1) throw new TypeError("offline");
    return response({ ok: true });
  });
  const client = runtime.createJsonClient("test", () => true);

  await assert.rejects(client.fetchJson("stats/test/one.json"));
  assert.equal((await client.fetchJson("stats/test/one.json")).ok, true);
  assert.equal(calls, 2);
});

test("concurrent readers share one in-flight request", async () => {
  let calls = 0;
  let release;
  const runtime = runtimeWith(() => {
    calls += 1;
    return new Promise(resolve => {
      release = () => resolve(response({ shared: true }));
    });
  });
  const client = runtime.createJsonClient("test", () => true);

  const first = client.fetchJson("stats/test/shared.json");
  const second = client.fetchJson("stats/test/shared.json");
  assert.equal(calls, 1);
  release();
  assert.equal((await first).shared, true);
  assert.equal((await second).shared, true);
});

test("successful entries use bounded least-recently-used eviction", async () => {
  const runtime = runtimeWith(async url => response({ url }));
  const client = runtime.createJsonClient("test", () => true, {
    maxBytes: 1024,
    maxEntries: 2,
  });

  await client.fetchJson("stats/test/a.json");
  await client.fetchJson("stats/test/b.json");
  await client.fetchJson("stats/test/a.json");
  await client.fetchJson("stats/test/c.json");

  assert.deepEqual([...client.snapshot().successPaths], [
    "stats/test/a.json",
    "stats/test/c.json",
  ]);
});

test("staged refreshes commit atomically and preserve old data on failure", async () => {
  const values = new Map([
    ["./stats/test/a.json", { version: 1 }],
    ["./stats/test/b.json", { version: 1 }],
  ]);
  const runtime = runtimeWith(async url => {
    const value = values.get(url);
    if (value instanceof Error) throw value;
    return response(value);
  });
  const client = runtime.createJsonClient("test", () => true);
  const aPath = "stats/test/a.json";
  const bPath = "stats/test/b.json";

  await client.fetchJson(aPath);
  await client.fetchJson(bPath);
  values.set(`./${aPath}`, { version: 2 });
  values.set(`./${bPath}`, new TypeError("offline"));
  await assert.rejects(client.stage([aPath, bPath]));
  assert.equal((await client.fetchJson(aPath)).version, 1);
  assert.equal((await client.fetchJson(bPath)).version, 1);

  values.set(`./${bPath}`, { version: 2 });
  const staged = await client.stage([aPath, bPath]);
  assert.equal(staged.changed, true);
  assert.equal((await client.fetchJson(aPath)).version, 1);
  staged.commit();
  assert.equal((await client.fetchJson(aPath)).version, 2);
  assert.equal((await client.fetchJson(bPath)).version, 2);
});

test("foreground timeouts release the in-flight request", async () => {
  let calls = 0;
  const runtime = runtimeWith((url, options) => {
    calls += 1;
    return new Promise((resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    });
  });
  const client = runtime.createJsonClient("test", () => true, {
    foregroundTimeoutMs: 5,
  });

  await assert.rejects(
    client.fetchJson("stats/test/slow.json"),
    error => error.code === "timeout"
  );
  await assert.rejects(client.fetchJson("stats/test/slow.json"));
  assert.equal(calls, 2);
});

test("the runtime admits only the exact generated manifest assets", () => {
  const runtime = runtimeWith(async () => response({}));

  assert.equal(
    runtime.publicPath("assets/card-cache/v1/manifest.json"),
    "./assets/card-cache/v1/manifest.json"
  );
  assert.equal(
    runtime.publicPath("assets/card-localization/cards.json"),
    "./assets/card-localization/cards.json"
  );
  assert.throws(() => runtime.publicPath("assets/card-cache/v1/images/card.jpg"));
  assert.throws(() => runtime.publicPath("assets/card-localization/images/card.webp"));
});

test("a recent admitted Landing week receives exact local card-image paths", async () => {
  const documents = landingDocuments();
  documents.set(
    "./assets/card-cache/v1/manifest.json",
    cardImageCacheManifest()
  );
  const controller = mtgoControllerWith(documents);

  const context = await controller.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null
  );

  assert.equal(
    context.featureImageCache["Cached Card"],
    "assets/card-cache/v1/images/11111111-1111-4111-8111-111111111111.jpg"
  );
});

test("an older Landing week does not consume the recent image cache", async () => {
  const documents = landingDocuments();
  documents.set("./stats/standard/mtgo/landing/features/index.json", {
    format: "standard",
    weeks: [
      { week: "2026-W33", file: "2026-W33.json", feature_count: 1 },
      { week: "2026-W29", file: "2026-W29.json", feature_count: 1 },
    ],
  });
  documents.set("./stats/standard/mtgo/landing/features/2026-W29.json", {
    format: "standard",
    week: { id: "2026-W29" },
    features: { items: [] },
  });
  documents.set(
    "./assets/card-cache/v1/manifest.json",
    cardImageCacheManifest()
  );
  const controller = mtgoControllerWith(documents);

  const context = await controller.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    "2026-W29.json"
  );

  assert.equal(context.featureFile, "2026-W29.json");
  assert.equal(context.featureImageCache, null);
});

test("a missing or unsafe cache manifest preserves the Scryfall fallback", async () => {
  const missingController = mtgoControllerWith(landingDocuments());
  const missing = await missingController.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null
  );
  assert.equal(missing.featureImageCache, null);

  const documents = landingDocuments();
  const unsafe = cardImageCacheManifest();
  unsafe.cards[0].local_path = "https://example.test/not-the-cache.jpg";
  documents.set("./assets/card-cache/v1/manifest.json", unsafe);
  const unsafeController = mtgoControllerWith(documents);
  const invalid = await unsafeController.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null
  );
  assert.equal(invalid.featureImageCache, null);

  const legacyDocuments = landingDocuments();
  const legacy = cardImageCacheManifest();
  legacy.schema_version = "1.0.0";
  legacy.cards[0].cache_source = "repository";
  legacy.cards[0].local_path = "assets/images/representative-cards/standard/cached-card.jpg";
  legacyDocuments.set("./assets/card-cache/v1/manifest.json", legacy);
  const legacyController = mtgoControllerWith(legacyDocuments);
  const legacyContext = await legacyController.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null
  );
  assert.equal(legacyContext.featureImageCache, null);
});

test("Landing keeps same-period companion documents", async () => {
  const controller = mtgoControllerWith(landingDocuments());

  const context = await controller.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null,
    { includeEnvironmentDecks: true, includeFeatureDecks: true }
  );

  assert.equal(context.range.total_decks, 70);
  assert.ok(context.completeness);
  assert.ok(context.environmentDecks);
  assert.ok(context.featureDecks);
});

test("retained Landing drops newer companion facts instead of failing", async () => {
  const controller = mtgoControllerWith(landingDocuments({ companionWeek: "2026-W34" }));

  const context = await controller.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    null,
    { includeEnvironmentDecks: true, includeFeatureDecks: true }
  );

  assert.equal(context.landing.week.id, "2026-W33");
  assert.equal(context.range, null);
  assert.equal(context.completeness, null);
  assert.equal(context.environmentDecks, null);
  assert.equal(context.featureDecks, null);
});

test("Landing still rejects a companion document from another format", async () => {
  const controller = mtgoControllerWith(landingDocuments({ rangeFormat: "modern" }));

  await assert.rejects(
    controller.loadLanding(
      "standard",
      "stats/standard/mtgo/landing/current.json",
      null
    ),
    error => error.code === "invalid"
  );
});
