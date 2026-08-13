"use strict";

const { chromium } = require("@playwright/test");

async function runBrowserPreflight(launch = () => chromium.launch()) {
  let browser;
  try {
    browser = await launch();
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`Chromium launch preflight failed: ${detail}`, { cause: error });
  }
  await browser.close();
}

module.exports = { runBrowserPreflight };
