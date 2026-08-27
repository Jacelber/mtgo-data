(function (root) {
  "use strict";

  const Runtime = root.P8Runtime;
  const ReviewData = root.P8ReviewData;
  const client = Runtime.createJsonClient(
    "实体大赛",
    path => /^stats\/[a-z0-9_-]+\/melee\//.test(path)
  );
  const CANONICAL_SCOPES = ["day1", "day2", "all_constructed"];
  const EVENT_ID_PATTERN = /^[1-9][0-9]*$/;

  function numericEventOrder(left, right) {
    return left.length - right.length || left.localeCompare(right);
  }

  function parseSelectedEventIds(value) {
    if (typeof value !== "string" || !value) return null;
    const eventIds = value.split(",");
    if (eventIds.some(eventId => !EVENT_ID_PATTERN.test(eventId))) return null;
    return [...new Set(eventIds)].sort(numericEventOrder);
  }

  function resolveEventSelection(events, selectedEventIds, activeEventId) {
    if (!Array.isArray(events) || !events.length) {
      throw new Error("实体大赛目录中没有可用赛事。");
    }
    const byId = new Map();
    events.forEach(event => {
      if (
        !EVENT_ID_PATTERN.test(event?.event_id || "")
        || byId.has(event.event_id)
      ) {
        throw new Error("实体大赛目录包含无效赛事身份。");
      }
      byId.set(event.event_id, event);
    });
    const requested = Array.isArray(selectedEventIds)
      ? [...new Set(selectedEventIds)].sort(numericEventOrder)
      : [];
    const admitted = requested.length
      && requested.every(eventId => EVENT_ID_PATTERN.test(eventId) && byId.has(eventId))
      ? requested
      : [byId.has(activeEventId) ? activeEventId : events[0].event_id];
    const activeId = admitted.includes(activeEventId) ? activeEventId : admitted[0];
    return {
      activeEvent: byId.get(activeId),
      eventEntries: admitted.map(eventId => byId.get(eventId)),
      eventIds: admitted,
    };
  }

  function canonicalMultiEventHierarchy(eventInputs, identityOrder) {
    if (!Array.isArray(identityOrder) || !identityOrder.length) {
      throw new Error("多赛事分类身份顺序不可用。");
    }
    const orderedIds = [...new Set([...identityOrder, "unknown"])];
    const order = new Map(orderedIds.map((identityId, position) => [identityId, position]));
    const parents = new Map();
    const leaves = new Map();
    eventInputs.forEach(input => {
      const hierarchy = input.matchup?.hierarchy;
      if (!Array.isArray(hierarchy?.parents) || !Array.isArray(hierarchy?.leaves)) {
        throw new Error("多赛事对局文档缺少分类身份层级。");
      }
      hierarchy.parents.forEach(parent => {
        if (!parents.has(parent.id)) parents.set(parent.id, parent);
      });
      hierarchy.leaves.forEach(leaf => {
        if (!leaves.has(leaf.id)) leaves.set(leaf.id, leaf);
      });
    });
    const compareIdentity = (left, right) => {
      if (!order.has(left) || !order.has(right)) {
        throw new Error("多赛事对局文档包含格式身份目录之外的分类身份。");
      }
      return order.get(left) - order.get(right);
    };
    const leafOrder = [...leaves.keys()].sort(compareIdentity);
    const parentOrder = [...parents.keys()].sort(compareIdentity);
    return {
      parents: parentOrder.map(parentId => ({
        ...parents.get(parentId),
        subtype_ids: leafOrder.filter(leafId => {
          const leaf = leaves.get(leafId);
          return leaf.parent_id === parentId && leaf.kind === "subtype";
        }),
      })),
      leaves: leafOrder.map(leafId => ({ ...leaves.get(leafId) })),
    };
  }

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
    {
      includeMatchup = false,
      includeDecks = false,
      selectedEventIds = null,
    } = {}
  ) {
    const index = await client.fetchJson(indexPath);
    const selection = resolveEventSelection(
      index.events,
      selectedEventIds || [selectedEventId].filter(Boolean),
      selectedEventId
    );
    const eventEntry = selection.activeEvent;

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
      selectedEventEntries: selection.eventEntries,
      tabletopDecks,
    };
  }

  async function loadMultiEventMatchups(
    indexPath,
    index,
    eventEntries,
    format,
    canonicalIdentityOrder
  ) {
    const base = Runtime.dirname(indexPath);
    const eventInputs = await Promise.all(eventEntries.map(async eventEntry => {
      const [meta, matchup] = await Promise.all([
        client.fetchJson(Runtime.joinPath(base, eventEntry.meta)),
        client.fetchJson(Runtime.joinPath(base, eventEntry.matchup)),
      ]);
      resolveEventFormat({
        requestedFormat: format,
        index,
        meta,
        matchup,
      });
      return { meta, matchup };
    }));
    const canonicalHierarchy = canonicalMultiEventHierarchy(
      eventInputs,
      canonicalIdentityOrder
    );
    return {
      eventInputs,
      multiEventMatchup: ReviewData.buildMultiEventMatchupContract(
        eventInputs,
        canonicalHierarchy,
        index
      ),
    };
  }

  async function stageEvent(
    indexPath,
    eventEntry,
    format,
    mtgoController,
    {
      includeMatchup = false,
      includeDecks = false,
      selectedEventEntries = null,
      canonicalIdentityOrder = null,
    } = {}
  ) {
    const base = Runtime.dirname(indexPath);
    const metaPath = Runtime.joinPath(base, eventEntry.meta);
    const overviewPath = Runtime.joinPath(base, eventEntry.overview);
    const qualityPath = Runtime.joinPath(base, eventEntry.quality);
    const matchupEntries = includeMatchup
      ? (selectedEventEntries?.length ? selectedEventEntries : [eventEntry])
      : [];
    const matchupPath = includeMatchup
      ? Runtime.joinPath(base, eventEntry.matchup)
      : null;
    const decksPath = includeDecks
      ? Runtime.joinPath(base, eventEntry.decks)
      : null;
    const paths = [indexPath, metaPath, overviewPath, qualityPath];
    matchupEntries.forEach(item => {
      paths.push(
        Runtime.joinPath(base, item.meta),
        Runtime.joinPath(base, item.matchup)
      );
    });
    if (decksPath) paths.push(decksPath);
    const [staged, mtgoStaged] = await Promise.all([
      client.stage(paths),
      includeDecks ? mtgoController.stageComparisonDecks(format) : null,
    ]);
    resolveEventFormat({
      requestedFormat: format,
      index: staged.get(indexPath),
      meta: staged.get(metaPath),
      overview: staged.get(overviewPath),
      matchup: matchupPath ? staged.get(matchupPath) : null,
      quality: staged.get(qualityPath),
      tabletopDecks: decksPath ? staged.get(decksPath) : null,
      mtgoDecks: mtgoStaged?.values[`stats/${format}/mtgo/decks_4w.json`],
    });
    if (matchupEntries.length > 1) {
      const eventInputs = matchupEntries.map(item => ({
        meta: staged.get(Runtime.joinPath(base, item.meta)),
        matchup: staged.get(Runtime.joinPath(base, item.matchup)),
      }));
      const canonicalHierarchy = canonicalMultiEventHierarchy(
        eventInputs,
        canonicalIdentityOrder
      );
      ReviewData.buildMultiEventMatchupContract(
        eventInputs,
        canonicalHierarchy,
        staged.get(indexPath)
      );
    }
    if (!mtgoStaged) return staged;
    return Object.freeze({
      changed: staged.changed || mtgoStaged.changed,
      commit() {
        staged.commit();
        mtgoStaged.commit();
      },
    });
  }

  root.P8TabletopController = Object.freeze({
    loadEvent,
    loadMultiEventMatchups,
    parseSelectedEventIds,
    resolveEventFormat,
    resolveEventSelection,
    resolveScopeState,
    stageEvent,
    structurePresentation,
  });
})(globalThis);
