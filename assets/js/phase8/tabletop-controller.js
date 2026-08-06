(function (root) {
  "use strict";

  const Runtime = root.P8Runtime;
  const client = Runtime.createJsonClient(
    "实体大赛",
    path => /^stats\/[a-z0-9_-]+\/melee\//.test(path)
  );
  const CANONICAL_SCOPES = ["day1", "day2", "all_constructed"];

  function resolveScopeState({
    events,
    selectedEventIds,
    activeEventId,
    requestedScope,
    preferredSingleScope,
    restoreSingleScope = false,
  }) {
    const byId = new Map(events.map(event => [event.event_id, event]));
    const selected = [...new Set(selectedEventIds)]
      .map(id => byId.get(id))
      .filter(Boolean);
    const active = byId.get(activeEventId) || selected[0] || events[0];
    if (!active) throw new Error("实体大赛目录中没有可用赛事。");

    const multiEvent = selected.length > 1;
    const scopeOrder = multiEvent
      ? CANONICAL_SCOPES.filter(scope => (
          selected.some(event => event.scope_order.includes(scope))
        ))
      : [...active.scope_order];
    const preferred = restoreSingleScope ? preferredSingleScope : requestedScope;
    const fallback = active.default_scope || "all_constructed";
    const scope = multiEvent
      ? "all_constructed"
      : scopeOrder.includes(preferred)
        ? preferred
        : scopeOrder.includes(requestedScope)
          ? requestedScope
          : scopeOrder.includes(fallback)
            ? fallback
            : scopeOrder[0];

    return {
      multi_event: multiEvent,
      scope,
      scope_order: scopeOrder,
      disabled_scopes: multiEvent
        ? scopeOrder.filter(item => item !== "all_constructed")
        : [],
    };
  }

  function structurePresentation(overview) {
    if (overview.event_structure === "constructed_day2") {
      return {
        advancement_metric: "day2_conversion",
        show_mixed_selection_bias: false,
      };
    }
    return {
      advancement_metric: "high_score",
      show_mixed_selection_bias: overview.event_structure === "mixed",
    };
  }

  function resolveEventFormat({
    requestedFormat,
    index,
    meta,
    overview,
    matchup,
    quality,
    tabletopDecks,
    mtgoDecks,
  }) {
    const eventFormat = meta?.format;
    const documents = [
      index,
      meta,
      overview,
      matchup,
      quality,
      tabletopDecks,
      mtgoDecks,
    ].filter(Boolean);
    if (
      !eventFormat
      || requestedFormat !== eventFormat
      || documents.some(document => document?.format !== eventFormat)
    ) {
      throw new Error("实体大赛文档的赛制不一致。");
    }
    return eventFormat;
  }

  async function loadEvent(
    indexPath,
    selectedEventId,
    format,
    mtgoController,
    { includeMatchup = false, includeDecks = false } = {}
  ) {
    const index = await client.fetchJson(indexPath);
    const eventEntry = index.events.find(item => item.event_id === selectedEventId)
      || index.events[0];
    if (!eventEntry) throw new Error("实体大赛目录中没有可用赛事。");

    const base = Runtime.dirname(indexPath);
    const [meta, overview, matchup, quality, tabletopDecks, mtgoDecks] = await Promise.all([
      client.fetchJson(Runtime.joinPath(base, eventEntry.meta)),
      client.fetchJson(Runtime.joinPath(base, eventEntry.overview)),
      includeMatchup
        ? client.fetchJson(Runtime.joinPath(base, eventEntry.matchup))
        : null,
      client.fetchJson(Runtime.joinPath(base, eventEntry.quality)),
      includeDecks
        ? client.fetchJson(Runtime.joinPath(base, eventEntry.decks))
        : null,
      includeDecks ? mtgoController.loadComparisonDecks(format) : null,
    ]);
    const eventFormat = resolveEventFormat({
      requestedFormat: format,
      index,
      meta,
      overview,
      matchup,
      quality,
      tabletopDecks,
      mtgoDecks,
    });

    return {
      eventFormat,
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

  root.P8TabletopController = Object.freeze({
    loadEvent,
    resolveEventFormat,
    resolveScopeState,
    structurePresentation,
  });
})(globalThis);
