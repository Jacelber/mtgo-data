"use strict";

const { runBrowserPreflight } = require("./browser-preflight.js");

runBrowserPreflight().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
