"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runBrowserPreflight } = require("../browser/browser-preflight.js");

test("browser preflight stops after the first systemic launch failure", async () => {
  let launches = 0;
  const launch = async () => {
    launches += 1;
    const error = new Error("spawn EPERM");
    error.code = "EPERM";
    throw error;
  };

  await assert.rejects(
    runBrowserPreflight(launch),
    /Chromium launch preflight failed: spawn EPERM/
  );
  assert.equal(launches, 1);
});

test("browser preflight closes a successfully launched browser", async () => {
  let closes = 0;
  await runBrowserPreflight(async () => ({
    close: async () => {
      closes += 1;
    },
  }));
  assert.equal(closes, 1);
});
