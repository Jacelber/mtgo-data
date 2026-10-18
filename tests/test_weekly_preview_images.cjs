const assert = require('node:assert/strict');
const { imageState, inspectImages } = require('../tools/weekly_preview_images.cjs');
const fake = (src, complete, width) => ({ currentSrc: src, getAttribute: () => src, alt: 'card', complete, naturalWidth: width });
assert.equal(imageState(fake('', true, 0)).state, 'not_requested');
assert.equal(imageState(fake('/good.jpg', false, 0)).state, 'loading');
assert.equal(imageState(fake('/good.jpg', true, 100)).state, 'loaded');
assert.equal(imageState(fake('/missing.jpg', true, 0)).state, 'failed');
(async () => {
  const images = [fake('', true, 0), fake('/missing.jpg', true, 0)];
  const locators = images.map((el, i) => ({
    locator: () => ({ isVisible: async () => true, scrollIntoViewIfNeeded: async () => {
      if (i === 0) Object.assign(el, fake('/lazy.jpg', true, 100));
    }}),
    evaluate: async fn => fn(el),
  }));
  const result = await inspectImages({ locator: () => ({ all: async () => locators }) });
  assert.equal(result[0].before, 'not_requested');
  assert.equal(result[0].loaded, true);
  assert.equal(result[1].state, 'failed');
  assert.equal(result[1].loaded, false);
  console.log('lazy-load success and real failure remain distinct: passed');
})().catch(e => { console.error(e); process.exitCode = 1; });
