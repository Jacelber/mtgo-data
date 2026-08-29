(function (root) {
  "use strict";

  const Runtime = root.P8Runtime;
  const CardLocalization = root.P8CardLocalization;
  const client = Runtime.createJsonClient(
    "MTGO",
    path => /^stats\/[a-z0-9_-]+\/mtgo\//.test(path)
  );
  const cardImageCacheManifestPath = "assets/card-cache/v1/manifest.json";
  const cardImageCacheClient = Runtime.createJsonClient(
    "Landing card-image cache",
    path => path === cardImageCacheManifestPath,
    { maxBytes: 1024 * 1024, maxEntries: 1, foregroundTimeoutMs: 5_000 }
  );
  const generatedCardImagePath = /^assets\/card-cache\/v1\/images\/[0-9a-f-]+(?:-face-[0-9]+)?\.jpg$/;
  const cardLocalizationClient = Runtime.createJsonClient(
    "Card localization",
    path => path === CardLocalization.LOOKUP_PATH,
    { maxBytes: 8 * 1024 * 1024, maxEntries: 1, foregroundTimeoutMs: 5_000 }
  );

  async function loadCardLocalization() {
    try {
      const value = await cardLocalizationClient.fetchJson(CardLocalization.LOOKUP_PATH);
      return CardLocalization.parseLookup(value);
    } catch (error) {
      if (error instanceof Runtime.ResourceError) return Object.freeze(Object.create(null));
      throw error;
    }
  }

  function rootPath(format) {
    return `stats/${format}/mtgo`;
  }

  async function loadStatistics(format, weeks, { includeDecks = false } = {}) {
    const base = rootPath(format);
    const [meta, range, decks, completeness] = await Promise.all([
      client.fetchJson(`${base}/meta.json`),
      client.fetchJson(`${base}/range_${weeks}w.json`),
      includeDecks ? client.fetchJson(`${base}/decks_${weeks}w.json`) : null,
      client.fetchJson(`${base}/completeness/${weeks}w.json`),
    ]);
    return { meta, range, decks, completeness };
  }

  function loadRangeStatistics(format, weeks) {
    return client.fetchJson(`${rootPath(format)}/range_${weeks}w.json`);
  }

  function landingPaths(format, landingPath, selectedFeatureFile, {
    includeEnvironmentDecks = false,
    includeFeatureDecks = false,
  } = {}) {
    const base = rootPath(format);
    const paths = [
      landingPath,
      `${base}/meta.json`,
      `${base}/range_1w.json`,
      `${base}/completeness/1w.json`,
      `${base}/landing/features/index.json`,
    ];
    if (selectedFeatureFile) {
      paths.push(`${base}/landing/features/${selectedFeatureFile}`);
    }
    if (includeEnvironmentDecks) paths.push(`${base}/decks_1w.json`);
    if (includeFeatureDecks) paths.push(`${base}/decks_4w.json`);
    return paths;
  }

  function validateLandingGroup(format, documents) {
    const {
      landing, range, completeness, featureIndex, featureDocument,
    } = documents;
    const periodMatches = landing.week?.start === range.period?.start
      && landing.week?.end === range.period?.end
      && landing.week?.start === completeness.period?.start
      && landing.week?.end === completeness.period?.end;
    const formatsMatch = [landing, range, completeness, featureIndex, featureDocument]
      .filter(Boolean)
      .every(document => !document.format || document.format === format);
    const selectedWeekMatches = !featureDocument
      || featureDocument.week?.id === documents.featureFile?.replace(/\.json$/, "");
    if (!formatsMatch || !selectedWeekMatches) {
      throw new Runtime.ResourceError("invalid", `${rootPath(format)}/landing/current.json`);
    }
    if (periodMatches) return documents;
    return {
      ...documents,
      range: null,
      completeness: null,
      environmentDecks: null,
      featureDecks: null,
    };
  }

  function featureImageCacheFor(manifest, format, week) {
    if (
      manifest?.schema_version !== "1.1.0"
      || manifest.product !== "mtgo-landing-card-image-cache"
      || manifest.public_prefix !== "assets/card-cache/v1"
      || manifest.window_size_weeks !== 4
      || !Array.isArray(manifest.formats)
      || !Array.isArray(manifest.cards)
    ) {
      return null;
    }
    const formatWindows = manifest.formats.filter(item => item?.format === format);
    if (
      formatWindows.length !== 1
      || !Array.isArray(formatWindows[0].selected_weeks)
      || !formatWindows[0].selected_weeks.includes(week)
    ) {
      return null;
    }
    const images = Object.create(null);
    for (const card of manifest.cards) {
      if (
        !card
        || typeof card.name !== "string"
        || !card.name
        || card.cache_source !== "generated"
        || typeof card.local_path !== "string"
        || !Array.isArray(card.uses)
      ) {
        return null;
      }
      const usedByWeek = card.uses.some(use => (
        use?.format === format
        && Array.isArray(use.weeks)
        && use.weeks.includes(week)
      ));
      if (!usedByWeek) continue;
      if (!generatedCardImagePath.test(card.local_path)) {
        return null;
      }
      if (images[card.name] && images[card.name] !== card.local_path) return null;
      images[card.name] = card.local_path;
    }
    return Object.freeze(images);
  }

  async function loadFeatureImageCache(format, week) {
    if (!week) return null;
    try {
      const manifest = await cardImageCacheClient.fetchJson(cardImageCacheManifestPath);
      return featureImageCacheFor(manifest, format, week);
    } catch (error) {
      if (error instanceof Runtime.ResourceError) return null;
      throw error;
    }
  }

  async function loadLanding(format, landingPath, selectedFeatureFile, options = {}) {
    const base = rootPath(format);
    const landing = await client.fetchJson(landingPath);
    const featureIndex = await client.fetchJson(`${base}/landing/features/index.json`);
    const selectableWeeks = featureIndex.weeks.filter(item => item.feature_count > 0);
    const selectableFeatureIndex = { ...featureIndex, weeks: selectableWeeks };
    const currentFeatureFile = `${landing.week?.id}.json`;
    const selectedEntry = selectableWeeks.find(item => item.file === selectedFeatureFile)
      || selectableWeeks.find(item => item.file === currentFeatureFile)
      || selectableWeeks[0]
      || null;
    const featureFile = selectedEntry?.file || null;
    const [
      meta,
      range,
      completeness,
      featureDocument,
      environmentDecks,
      featureDecks,
      featureImageCache,
    ] = await Promise.all([
      client.fetchJson(`${base}/meta.json`),
      client.fetchJson(`${base}/range_1w.json`),
      client.fetchJson(`${base}/completeness/1w.json`),
      featureFile ? client.fetchJson(`${base}/landing/features/${featureFile}`) : null,
      options.includeEnvironmentDecks ? client.fetchJson(`${base}/decks_1w.json`) : null,
      options.includeFeatureDecks ? client.fetchJson(`${base}/decks_4w.json`) : null,
      loadFeatureImageCache(format, selectedEntry?.week),
    ]);
    return validateLandingGroup(format, {
      landing,
      meta,
      range,
      completeness,
      featureIndex: selectableFeatureIndex,
      featureEntry: selectedEntry,
      featureDocument,
      featureFile,
      featureImageCache,
      environmentDecks,
      featureDecks,
    });
  }

  async function loadMatchup(format, weeks) {
    const base = rootPath(format);
    const [document, completeness] = await Promise.all([
      client.fetchJson(`${base}/matchup_${weeks}w.json`),
      client.fetchJson(`${base}/completeness/${weeks}w.json`),
    ]);
    return { document, completeness };
  }

  async function loadTop8(indexPath, selectedFile, { includeBases = false } = {}) {
    const index = await client.fetchJson(indexPath);
    const weekEntry = index.weeks.find(item => item.file === selectedFile)
      || index.weeks[0];
    if (!weekEntry) throw new Error("MTGO 八强目录中没有可用周。");
    const base = Runtime.dirname(indexPath);
    const [top8, bases] = await Promise.all([
      client.fetchJson(Runtime.joinPath(base, weekEntry.file)),
      includeBases
        ? client.fetchJson(Runtime.joinPath(base, weekEntry.comparison_bases_file))
        : null,
    ]);
    return { index, weekEntry, top8, bases };
  }

  function loadComparisonDecks(format) {
    return client.fetchJson(`${rootPath(format)}/decks_4w.json`);
  }

  function requireFormat(staged, paths, format) {
    if (paths.some(path => {
      const document = staged.get(path);
      return document?.format && document.format !== format;
    })) {
      throw new Runtime.ResourceError("invalid", paths[0]);
    }
    return staged;
  }

  async function stageStatistics(format, weeks, { includeDecks = false } = {}) {
    const base = rootPath(format);
    const paths = [
      `${base}/meta.json`,
      `${base}/range_${weeks}w.json`,
      `${base}/completeness/${weeks}w.json`,
    ];
    if (includeDecks) paths.push(`${base}/decks_${weeks}w.json`);
    return requireFormat(await client.stage(paths), paths, format);
  }

  async function stageLanding(format, landingPath, selectedFeatureFile, options = {}) {
    const paths = landingPaths(format, landingPath, selectedFeatureFile, options);
    return requireFormat(await client.stage(paths), paths, format);
  }

  async function stageComparisonDecks(format) {
    const path = `${rootPath(format)}/decks_4w.json`;
    return requireFormat(await client.stage([path]), [path], format);
  }

  async function stageMatchup(format, weeks) {
    const base = rootPath(format);
    const paths = [
      `${base}/matchup_${weeks}w.json`,
      `${base}/completeness/${weeks}w.json`,
    ];
    return requireFormat(await client.stage(paths), paths, format);
  }

  async function stageTop8(
    indexPath,
    selectedFile,
    { comparisonBasesFile = null } = {}
  ) {
    const base = Runtime.dirname(indexPath);
    const top8Path = Runtime.joinPath(base, selectedFile);
    const paths = [indexPath, top8Path];
    if (comparisonBasesFile) {
      paths.push(Runtime.joinPath(base, comparisonBasesFile));
    }
    const staged = await client.stage(paths);
    const index = staged.get(indexPath);
    const week = index.weeks.find(item => item.file === selectedFile);
    if (
      (index.format && index.format !== staged.get(top8Path)?.format)
      || !week
      || (comparisonBasesFile && week.comparison_bases_file !== comparisonBasesFile)
    ) {
      throw new Runtime.ResourceError("invalid", indexPath);
    }
    return staged;
  }

  root.P8MtgoController = Object.freeze({
    loadCardLocalization,
    loadComparisonDecks,
    loadMatchup,
    loadLanding,
    loadRangeStatistics,
    loadStatistics,
    loadTop8,
    stageComparisonDecks,
    stageMatchup,
    stageLanding,
    stageStatistics,
    stageTop8,
  });
})(globalThis);
