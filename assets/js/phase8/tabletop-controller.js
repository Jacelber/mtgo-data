(function (root) {
  "use strict";

  const Runtime = root.P8Runtime;
  const client = Runtime.createJsonClient(
    "实体大赛",
    path => /^stats\/[a-z0-9_-]+\/melee\//.test(path)
  );

  async function loadEvent(indexPath, selectedEventId, format, mtgoController) {
    const index = await client.fetchJson(indexPath);
    const eventEntry = index.events.find(item => item.event_id === selectedEventId)
      || index.events[0];
    if (!eventEntry) throw new Error("实体大赛目录中没有可用赛事。");

    const base = Runtime.dirname(indexPath);
    const eventPaths = ["meta", "overview", "matchup", "quality", "decks"]
      .map(key => Runtime.joinPath(base, eventEntry[key]));
    const [meta, overview, matchup, quality, tabletopDecks, mtgoDecks] = await Promise.all([
      ...eventPaths.map(path => client.fetchJson(path)),
      mtgoController.loadComparisonDecks(format),
    ]);

    return {
      eventEntry,
      index,
      matchup,
      meta,
      mtgoDecks,
      overview,
      quality,
      tabletopDecks,
    };
  }

  root.P8TabletopController = Object.freeze({ loadEvent });
})(globalThis);
