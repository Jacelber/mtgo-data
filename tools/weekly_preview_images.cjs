// Load visible image frames before judging them. A lazy placeholder is not a
// failed download; failure to load after scrolling still fails the page check.
function imageState(image) {
  const src = image.currentSrc || image.getAttribute('src') || '';
  return { src, alt: image.alt, state: !src ? 'not_requested'
    : image.complete ? (image.naturalWidth > 0 ? 'loaded' : 'failed') : 'loading' };
}

async function inspectImages(region) {
  const results = [];
  for (const image of await region.locator('img').all()) {
    const frame = image.locator('xpath=..');
    if (!(await frame.isVisible())) continue;
    const before = await image.evaluate(imageState);
    await frame.scrollIntoViewIfNeeded();
    await image.evaluate(el => new Promise(resolve => {
      if ((el.currentSrc || el.getAttribute('src')) && el.complete) return resolve();
      const finish = () => {
        clearTimeout(timer);
        el.removeEventListener('load', finish);
        el.removeEventListener('error', finish);
        resolve();
      };
      const timer = setTimeout(finish, 5000);
      el.addEventListener('load', finish, { once: true });
      el.addEventListener('error', finish, { once: true });
    }));
    const after = await image.evaluate(imageState);
    results.push({ ...after, before: before.state, loaded: after.state === 'loaded' });
  }
  return results;
}

module.exports = { imageState, inspectImages };
