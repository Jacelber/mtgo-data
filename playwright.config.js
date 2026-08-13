"use strict";

const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/browser",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "node tests/browser/static-server.js",
    url: "http://127.0.0.1:4173/stats/catalog.json",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
