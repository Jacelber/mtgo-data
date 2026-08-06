(function (root) {
  "use strict";

  const Runtime = root.P8Runtime;
  const client = Runtime.createJsonClient(
    "MTGO",
    path => /^stats\/[a-z0-9_-]+\/mtgo\//.test(path)
  );

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

  async function loadPickup(indexPath, selectedFile) {
    const index = await client.fetchJson(indexPath);
    const week = index.weeks.find(item => item.file === selectedFile)
      || index.weeks[0];
    if (!week) throw new Error("每周精选目录中没有可用周。");
    const document = await client.fetchJson(
      Runtime.joinPath(Runtime.dirname(indexPath), week.file)
    );
    return { index, week, document };
  }

  function loadComparisonDecks(format) {
    return client.fetchJson(`${rootPath(format)}/decks_4w.json`);
  }

  root.P8MtgoController = Object.freeze({
    loadComparisonDecks,
    loadMatchup,
    loadPickup,
    loadStatistics,
    loadTop8,
  });
})(globalThis);
