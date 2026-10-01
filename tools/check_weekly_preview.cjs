// Only the selected Landing and its actual bilingual resources. No publication.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { chromium } = require(process.env.WEEKLY_PLAYWRIGHT || 'playwright');

(async () => {
  const [base, format, output, site, onlyFeature] = process.argv.slice(2);
  fs.mkdirSync(output, { recursive: true });
  const context = vm.createContext({ URL, P8Runtime: { createJsonClient: () => ({}) } });
  for (const file of ['card-localization.js', 'archetype-visuals.js']) {
    vm.runInContext(fs.readFileSync(path.join(site, 'assets/js/phase8', file), 'utf8'), context);
  }
  // Use the current pure consumer selector, including for retained renderers
  // whose public object did not yet expose that function.
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/js/phase8/mtgo-controller.js'), 'utf8'), context);
  const read = relative => JSON.parse(fs.readFileSync(path.join(site, relative), 'utf8'));
  const document = read(`stats/${format}/mtgo/landing/current.json`);
  const lookup = context.P8CardLocalization.parseLookup(read('assets/card-localization/cards.json'));
  const cache = context.P8MtgoController.featureImageCacheFor(read('assets/card-cache/v1/manifest.json'), format, document.week.id) || {};
  const selected = [];
  if (!onlyFeature) for (const row of document.environment.rows) {
    for (const card of context.P8ArchetypeVisuals.representativeCards[format]?.[row.archetype_id] || []) {
      selected.push({ name: card.name, image: 'assets/' + card.image.slice(3), region: 'environment:' + row.archetype_id });
    }
  }
  const features = document.features.items.filter(item => !onlyFeature || item.destination_id === onlyFeature);
  if (onlyFeature && features.length !== 1) throw new Error('Requested Feature is not present exactly once');
  for (const feature of features) for (const card of feature.featured_cards) selected.push({ name: card.name, image: cache[card.name], region: 'feature:' + feature.destination_id });
  const resources = [];
  for (const language of ['zh', 'en']) for (const card of selected) {
    const chosen = context.P8CardLocalization.resolve(card.name, language, lookup, card.image);
    const local = chosen.image && !/^[a-z]+:/i.test(chosen.image) && !chosen.image.split('/').includes('..');
    const file = local ? path.join(site, chosen.image) : null;
    resources.push({ region: card.region, language, name: card.name, selected: chosen.image, source: chosen.source,
      display_name: chosen.displayName, link: chosen.linkUrl,
      exists: !!file && fs.existsSync(file), sha256: file && fs.existsSync(file)
        ? crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') : null });
  }
  fs.writeFileSync(path.join(output, 'resources.json'), JSON.stringify(resources, null, 2));
  if (resources.some(item => !item.exists)) {
    console.log(JSON.stringify({ passed: false, phase: 'resource-preflight', missing: resources.filter(item => !item.exists) }));
    process.exitCode = 1; return;
  }
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const language of ['zh', 'en']) {
      const page = await browser.newPage({ viewport: { width: 1365, height: 1000 } });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
      // Isolation: external network is blocked and reported, never fetched to
      // disguise missing local resources during a cache-hit replay.
      const external = [];
      await page.route('**/*', route => {
        if (new URL(route.request().url()).origin !== new URL(base).origin) {
          external.push(route.request().url());
          return route.abort();
        }
        return route.continue();
      });
      await page.goto(`${base}/index.html?format=${format}&view=landing&lang=${language}`, { waitUntil: 'networkidle' });
      await page.locator('body').waitFor();
      if (await page.locator('.landing-feature-item').count() !== document.features.items.length) {
        errors.push('Rendered Feature count differs from the fixed page');
      }
      // Exercise lazy loading as a reader does. A full-page screenshot alone
      // does not put below-the-fold images into the viewport.
      for (const detail of await page.locator('details').all()) {
        if (await detail.isVisible() && !(await detail.getAttribute('open'))) {
          await detail.locator('summary').click();
        }
      }
      const region = onlyFeature ? page.locator(`[data-feature-destination="${onlyFeature}"]`) : page.locator('body');
      for (const img of await region.locator('img').all()) {
        const frame = img.locator('xpath=..');
        if (!(await frame.isVisible())) continue;
        await frame.scrollIntoViewIfNeeded();
        await img.evaluate(el => new Promise(resolve => {
          if (el.complete && el.naturalWidth) return resolve();
          const timer = setTimeout(resolve, 5000);
          el.addEventListener('load', () => { clearTimeout(timer); resolve(); }, { once: true });
          el.addEventListener('error', () => { clearTimeout(timer); resolve(); }, { once: true });
        }));
      }
      const images = await region.locator('img').evaluateAll(elements => elements.filter(el => el.getClientRects().length).map(el => ({
        src: el.currentSrc || el.src, alt: el.alt, loaded: el.complete && el.naturalWidth > 0
      })));
      const text = await page.locator('body').innerText();
      const entry = { language, url: page.url(), images, external, errors,
        text: text.slice(0, 3000), passed: images.length > 0 && images.every(x => x.loaded) && !errors.length && !external.length };
      if (onlyFeature) await region.screenshot({ path: path.join(output, `${language}.png`) });
      else await page.screenshot({ path: path.join(output, `${language}.png`), fullPage: true });
      results.push(entry);
      await page.close();
    }
  } finally { await browser.close(); }
  const result = { passed: results.every(r => r.passed), results };
  fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ passed: result.passed, evidence: path.join(output, 'browser.json') }));
  process.exitCode = result.passed ? 0 : 1;
})().catch(error => { console.error(error); process.exitCode = 2; });
