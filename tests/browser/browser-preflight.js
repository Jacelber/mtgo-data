"use strict";

async function launchChromium() {
  const { chromium } = require("@playwright/test");
  return chromium.launch();
}

async function runBrowserPreflight(launch = launchChromium) {
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
