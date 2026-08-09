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
