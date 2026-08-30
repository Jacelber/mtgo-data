"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/app-card-preview.js"),
  "utf8"
);

function fakeClassList(...initial) {
  const values = new Set(initial);
  return {
    add: (...names) => names.forEach(name => values.add(name)),
    contains: name => values.has(name),
    remove: (...names) => names.forEach(name => values.delete(name)),
    replace: (from, to) => {
      if (!values.delete(from)) return false;
      values.add(to);
      return true;
    },
    toggle: (name, force) => {
      if (force === undefined) {
        if (values.has(name)) values.delete(name);
        else values.add(name);
        return values.has(name);
      }
      if (force) values.add(name);
      else values.delete(name);
      return force;
    },
  };
}

function fakeNode() {
  return {
    classList: fakeClassList(),
    dataset: {},
    disabled: false,
    hidden: false,
    inert: false,
    style: { removeProperty: () => {} },
    textContent: "",
    addEventListener: () => {},
    contains: () => false,
    focus: () => {},
    querySelector: () => null,
    querySelectorAll: () => [],
    removeAttribute(name) {
      delete this[name];
    },
    setAttribute(name, value) {
      this[name] = value;
    },
  };
}

function harness({ touch = false } = {}) {
  let now = 0;
  let timerId = 0;
  const timers = [];
  const starts = [];
  const listeners = new Map();

  function setTimer(callback, delay = 0) {
    const timer = { callback, due: now + delay, id: ++timerId, cancelled: false };
    timers.push(timer);
    return timer.id;
  }

  function clearTimer(id) {
    const timer = timers.find(candidate => candidate.id === id);
    if (timer) timer.cancelled = true;
  }

  function advance(milliseconds) {
    const target = now + milliseconds;
    while (true) {
      const next = timers
        .filter(timer => !timer.cancelled && timer.due <= target)
        .sort((left, right) => left.due - right.due || left.id - right.id)[0];
      if (!next) break;
      next.cancelled = true;
      now = next.due;
      next.callback();
    }
    now = target;
  }

  class ProbeImage {
    set src(url) {
      if (!url) return;
      this.url = url;
      starts.push({ at: now, probe: this, url });
    }
  }

  const floating = fakeNode();
  const floatingFrame = fakeNode();
  const floatingImage = fakeNode();
  const floatingStatus = fakeNode();
  floating.querySelector = selector => ({
    ".card-image-frame": floatingFrame,
    "img": floatingImage,
    ".card-image-placeholder": floatingStatus,
  })[selector] || null;

  const modal = fakeNode();
  modal.hidden = true;
  const dialog = fakeNode();
  const modalFrame = fakeNode();
  const modalImage = fakeNode();
  const modalTitle = fakeNode();
  const modalStatus = fakeNode();
  const modalRetry = fakeNode();
  const modalClose = fakeNode();
  const scryfallLink = fakeNode();
  modal.querySelector = selector => ({
    ".card-preview-dialog": dialog,
    ".card-image-frame": modalFrame,
    "img": modalImage,
    "#card-preview-title": modalTitle,
    "[data-card-image-status]": modalStatus,
    "[data-card-image-retry]": modalRetry,
    "[data-card-preview-close]": modalClose,
    "#card-preview-scryfall": scryfallLink,
  })[selector] || null;

  const body = fakeNode();
  const background = fakeNode();
  const document = {
    activeElement: null,
    body,
    hidden: false,
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(listener);
    },
    querySelector(selector) {
      if (selector === "#card-preview") return floating;
      if (selector === "#card-preview-modal") return modal;
      return background;
    },
    querySelectorAll: () => [],
  };
  const window = {
    addEventListener: () => {},
    history: { back: () => {}, pushState: () => {}, state: null },
    innerHeight: 720,
    innerWidth: 1280,
    location: { href: "http://localhost/index.html" },
    scrollTo: () => {},
    scrollY: 0,
  };
  const context = {
    Date: { now: () => now },
    Image: ProbeImage,
    clearTimeout: clearTimer,
    console: { error: () => {} },
    document,
    matchMedia: () => ({ matches: touch }),
    setTimeout: setTimer,
    t: key => key,
    window,
  };
  context.globalThis = context;
  vm.runInNewContext(source, context);

  return {
    advance,
    images: context.P8CardImages,
    listeners,
    modal,
    scryfallLink,
    starts,
  };
}

async function flushPromises() {
  for (let index = 0; index < 5; index += 1) await Promise.resolve();
}

test("card images start one at a time with at least 150ms between requests", async () => {
  const { advance, images, starts } = harness();
  const first = images.load("one");
  const second = images.load("two");
  const third = images.load("three");

  assert.deepEqual(starts.map(item => [item.url, item.at]), [["one", 0]]);
  starts[0].probe.onload();
  advance(149);
  assert.equal(starts.length, 1);
  advance(1);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [["one", 0], ["two", 150]]);
  starts[1].probe.onload();
  advance(150);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [
    ["one", 0], ["two", 150], ["three", 300],
  ]);
  starts[2].probe.onload();

  assert.deepEqual(await Promise.all([first, second, third]), ["one", "two", "three"]);
});

test("the final image in a 56-card Feature batch starts without queue-age failure", async () => {
  const { advance, images, starts } = harness();
  const urls = Array.from({ length: 56 }, (_, index) => `card-${index}`);
  const results = urls.map(url => images.load(url));

  for (let index = 0; index < urls.length; index += 1) {
    assert.equal(starts[index].url, urls[index]);
    starts[index].probe.onload();
    if (index < urls.length - 1) advance(150);
  }

  assert.equal(starts.at(-1).at, 8_250);
  assert.deepEqual(await Promise.all(results), urls);
});

test("a queued image receives its timeout only after its own request starts", async () => {
  const { advance, images, starts } = harness();
  const first = images.load("one").catch(error => error.code);
  const second = images.load("two").catch(error => error.code);

  advance(14_999);
  assert.equal(starts.length, 1);
  advance(1);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [["one", 0], ["two", 15_000]]);
  assert.equal(await first, "timeout");

  advance(14_999);
  assert.equal(await Promise.race([second, Promise.resolve("pending")]), "pending");
  advance(1);
  assert.equal(await second, "timeout");
});

test("a progressive image retries once after a bounded backoff", async () => {
  const { advance, images, starts } = harness();
  const result = images.load("retry", { autoRetry: true });

  starts[0].probe.onerror();
  advance(1_499);
  assert.equal(starts.length, 1);
  advance(1);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [["retry", 0], ["retry", 1_500]]);
  starts[1].probe.onload();

  assert.equal(await result, "retry");
  assert.equal(images.attempts("retry"), 2);
});

test("a priority preview preempts a delayed retry without breaking the start interval", async () => {
  const { advance, images, starts } = harness();
  const progressive = images.load("progressive", { autoRetry: true });
  starts[0].probe.onerror();

  advance(100);
  const preview = images.load("preview", { priority: true });
  advance(49);
  assert.equal(starts.length, 1);
  advance(1);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [
    ["progressive", 0], ["preview", 150],
  ]);
  starts[1].probe.onload();
  advance(1_350);
  assert.deepEqual(starts.map(item => [item.url, item.at]), [
    ["progressive", 0], ["preview", 150], ["progressive", 1_500],
  ]);
  starts[2].probe.onload();

  assert.deepEqual(await Promise.all([progressive, preview]), ["progressive", "preview"]);
});

test("cancelling a stale view removes only its queued work", async () => {
  const { advance, images, starts } = harness();
  const active = images.load("active", { owner: "view" });
  const stale = images.load("stale", { owner: "view" }).catch(error => error.code);
  const preview = images.load("preview", { owner: "preview" });

  images.cancelQueued("view");
  assert.equal(images.snapshot().queued, 1);
  assert.equal(await stale, "cancelled");
  starts[0].probe.onload();
  advance(150);
  assert.deepEqual(starts.map(item => item.url), ["active", "preview"]);
  starts[1].probe.onload();

  assert.deepEqual(await Promise.all([active, preview]), ["active", "preview"]);
});

test("an exhausted Feature image exposes a group retry that restores the inline image", async () => {
  const { advance, images, listeners, starts } = harness();
  const frame = fakeNode();
  frame.classList = fakeClassList("card-image-frame", "is-loading");
  const retryButton = fakeNode();
  retryButton.hidden = true;
  retryButton.textContent = "card.image_retry_group";
  const feature = fakeNode();
  const image = fakeNode();
  image.dataset.progressiveImage = "feature";
  image.closest = selector => {
    if (selector === ".card-image-frame") return frame;
    if (selector === ".landing-feature-item") return feature;
    return null;
  };
  retryButton.closest = selector => selector === ".landing-feature-item" ? feature : null;
  retryButton.closestTarget = selector => selector === "[data-retry-feature-images]" ? retryButton : null;
  feature.querySelector = selector => selector === "[data-retry-feature-images]" ? retryButton : null;
  feature.querySelectorAll = selector => selector.includes("data-progressive-image") ? [image] : [];
  const container = {
    querySelectorAll: () => [image],
  };

  images.observe(container);
  starts[0].probe.onerror();
  advance(1_500);
  starts[1].probe.onerror();
  await flushPromises();
  assert.equal(frame.classList.contains("is-error"), true);
  assert.equal(retryButton.hidden, false);

  const target = {
    closest(selector) {
      if (selector === "[data-retry-feature-images]") return retryButton;
      return null;
    },
  };
  listeners.get("click")[0]({ preventDefault: () => {}, target });
  assert.equal(retryButton.disabled, true);
  advance(150);
  starts[2].probe.onload();
  await flushPromises();

  assert.equal(image.src, "feature");
  assert.equal(frame.classList.contains("is-loaded"), true);
  assert.equal(retryButton.hidden, true);
});

test("touch preview uses the card link provider selected by the current language", () => {
  for (const expected of [
    { provider: "mtgch", url: "https://mtgch.com/card/ACR/276/", label: "card.view_mtgch" },
    { provider: "scryfall", url: "https://scryfall.com/search?q=test", label: "card.view_scryfall" },
  ]) {
    const { listeners, modal, scryfallLink } = harness({ touch: true });
    const link = fakeNode();
    link.dataset.cardImage = "card-image";
    link.dataset.cardName = "Card";
    link.dataset.cardProvider = expected.provider;
    link.dataset.cardUrl = expected.url;
    link.textContent = "Card";
    link.closest = selector => selector === "a[data-card-image]" ? link : null;

    listeners.get("click")[0]({ preventDefault: () => {}, target: link });

    assert.equal(modal.hidden, false);
    assert.equal(scryfallLink.href, expected.url);
    assert.equal(scryfallLink.textContent, expected.label);
  }
});
