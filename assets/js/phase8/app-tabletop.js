"use strict";

function scopeLabel(scope, formatId) {
  return I18n.tabletopScopeLabel(scope, formatId);
}

function eventDateRange(date) {
  if (!date) return "—";
  if (typeof date === "string") return date;
  return date.start === date.end ? date.start : `${date.start} ～ ${date.end}`;
}

function eventStructureLabel(value) {
  const key = {
    mixed: "tabletop.structure.mixed",
    constructed_day2: "tabletop.structure.constructed_day2",
    constructed_single_stage: "tabletop.structure.constructed_single_stage",
  }[value];
  return key ? t(key) : value;
}

function qualityStatusLabel(value) {
  const key = {
    ok: "tabletop.quality.ok",
    warning: "tabletop.quality.warning",
    blocked: "tabletop.quality.blocked",
  }[value];
  return key ? t(key) : value;
}

function issueMessage(issue, formatId) {
  const key = {
    unknown_classifications: "tabletop.issue.unknown",
    disqualified_participant_matches_excluded: "tabletop.issue.disqualified",
    mixed_event_day2_selection_bias: "tabletop.day2_bias",
    overall_standings_include_non_constructed_results: "tabletop.issue.overall_standings",
  }[issue.code];
  return key ? t(key, { format: formatLabel(formatId) }) : issue.message;
}

function overviewRecord(record) {
  return record?.literal_record || record;
}

function eventDeckMatchesIdentity(deck, identityId) {
  const [archetypeId, subtypeId] = identityId.split("/");
  return deck.classification?.archetype_id === archetypeId
    && (!subtypeId || deck.classification?.subtype_id === subtypeId);
}

function bestEventDeck(identityId, scopeId) {
  const candidates = (currentContext.tabletopDecks?.decks || []).filter(deck => {
    const scope = deck.scopes?.[scopeId];
    return eventDeckMatchesIdentity(deck, identityId)
      && deck.participant_status !== "disqualified"
      && !deck.statistics_eligibility?.played_match_metrics_excluded
      && deck.decklist?.status === "submitted"
      && deck.decklist?.cards?.length
      && scope?.participated;
  });
  candidates.sort((left, right) => {
    const a = left.scopes[scopeId];
    const b = right.scopes[scopeId];
    return (b.average_points_per_effective_round ?? -1) - (a.average_points_per_effective_round ?? -1)
      || (b.constructed_points ?? -1) - (a.constructed_points ?? -1)
      || (b.played_record?.wins ?? -1) - (a.played_record?.wins ?? -1)
      || String(left.participant_id).localeCompare(String(right.participant_id));
  });
  return candidates[0] || null;
}

function eventDeckForDisplay(deck) {
  if (!deck) return null;
  const cards = deck.decklist.cards || [];
  return {
    player: deck.player_name,
    final_rank: deck.final_rank,
    main_deck: cards.filter(card => card.section === "main").map(card => ({ name: card.name, qty: card.quantity })),
    side_deck: cards.filter(card => card.section === "sideboard").map(card => ({ name: card.name, qty: card.quantity })),
  };
}

function tabletopDetailRow(identityId) {
  const source = bestEventDeck(identityId, state.tabletopScope);
  const exactDeck = eventDeckForDisplay(source);
  const mtgoBase = locateDeck(currentContext.mtgoDecks, identityId);
  const performance = source?.scopes?.[state.tabletopScope];
  const record = performance?.played_record;
  const title = source?.classification?.subtype_name
    ? `${source.classification.subtype_name} ${source.classification.archetype_name}`
    : (source?.classification?.archetype_name || currentContext.tabletopIdentityNames.get(identityId) || identityId);
  const performanceHtml = performance ? `<div class="event-deck-performance">
    <strong>${t("tabletop.scope_performance", {
      scope: scopeLabel(state.tabletopScope, currentContext.eventFormat),
    })}</strong>
    <span>${t("tabletop.performance_summary", {
      average: number(performance.average_points_per_effective_round),
      points: performance.constructed_points,
      record: record ? `${record.wins}-${record.losses}-${record.draws}` : t("tabletop.no_valid_matches"),
    })}</span>
    <small>${t("tabletop.selection_rule")}</small>
  </div>` : "";
  return `<tr class="deck-detail-row"><td colspan="9">${deckDetailHtml({
    title,
    exactDeck,
    exactDeckTitle: t("tabletop.best_deck"),
    averageDeck: mtgoBase?.average_deck,
    comparison: { date: eventDateRange(currentContext.overview.event.date) },
    closeAction: "data-close-tabletop-detail",
    referenceNote: t("tabletop.mtgo_reference"),
    performanceHtml,
    showDeviation: false,
  })}</td></tr>`;
}

function tabletopOverall(scope, advancementMetric) {
  const counts = {
    wins: scope.result_counts.played_win || 0,
    losses: scope.result_counts.played_loss || 0,
    draws: scope.result_counts.played_draw || 0,
  };
  const record = ReviewData.literalRecord(counts);
  const dropRounds = scope.result_counts.drop_unplayed || 0;
  const completion = scope.theoretical_rounds
    ? (scope.theoretical_rounds - dropRounds) / scope.theoretical_rounds
    : null;
  return {
    name: t("tabletop.overall"),
    overall: true,
    deck_count: scope.participant_count,
    metagame_share: 1,
    average_points_per_effective_round: scope.average_points_per_effective_round,
    completion_rate: completion,
    day2_conversion: scope.day2_conversion,
    high_score: scope.high_score_deck_count === null ? null : { count: scope.high_score_deck_count },
    literal_record: record,
    subtypes: [],
  };
}

function tabletopRow(record, className = "", advancementMetric = "high_score") {
  const match = record.literal_record || overviewRecord(record.match_record?.all_matches);
  const advancement = advancementMetric === "day2_conversion"
    ? pct(record.day2_conversion)
    : (record.high_score?.count ?? "—");
  return `<tr class="${className}">
    <td class="identity-cell">${record.nameHtml || escapeHtml(record.display_name || record.archetype_name || record.name)}</td>
    <td class="number">${record.deck_count}</td><td class="number">${pct(record.metagame_share)}</td>
    <td class="number">${number(record.average_points_per_effective_round)}</td>
    <td class="number">${pct(match?.win_rate)}</td>
    <td class="number">${match ? `${match.wins}-${match.losses}-${match.draws}` : "—"}</td>
    <td class="number">${match?.matches ?? "—"}</td><td class="number">${pct(record.completion_rate)}</td>
    <td class="number">${advancement}</td>
  </tr>`;
}

function tabletopSortValue(record, key) {
  if (key === "name") return (record.archetype_name || record.display_name || "").toLowerCase();
  if (key === "win_rate") return overviewRecord(record.match_record?.all_matches)?.win_rate ?? -1;
  if (key === "matches") return overviewRecord(record.match_record?.all_matches)?.matches ?? -1;
  if (key === "day2_conversion") return record.day2_conversion ?? -1;
  if (key === "high_score") return record.high_score?.count ?? -1;
  return record[key] ?? -1;
}

function sortedTabletopArchetypes(archetypes) {
  const direction = state.tabletopDirection === "asc" ? 1 : -1;
  return [...archetypes].sort((left, right) => {
    const a = tabletopSortValue(left, state.tabletopSort);
    const b = tabletopSortValue(right, state.tabletopSort);
    return a < b ? -direction : a > b ? direction : 0;
  });
}

function activeTabletopSubtypes(parent) {
  return (parent.subtypes || []).filter(subtype => Number(subtype.deck_count) > 0);
}

function tabletopOverview(scope, presentation) {
  const advancementMetric = presentation.advancement_metric;
  const identityNames = new Map();
  scope.archetypes.forEach(parent => {
    if (parent.archetype_id) identityNames.set(parent.archetype_id, parent.archetype_name);
    activeTabletopSubtypes(parent).forEach(subtype => {
      identityNames.set(`${parent.archetype_id}/${subtype.subtype_id}`, subtype.display_name);
    });
  });
  currentContext.tabletopIdentityNames = identityNames;
  const rows = sortedTabletopArchetypes(scope.archetypes).map(parent => {
    const subtypes = activeTabletopSubtypes(parent);
    const expandable = subtypes.length >= 2;
    const open = expandable && state.tabletopExpanded.has(parent.archetype_id);
    const parentIdentity = parent.archetype_id;
    const directIdentity = subtypes.length === 1
      ? `${parent.archetype_id}/${subtypes[0].subtype_id}`
      : parentIdentity;
    const nameHtml = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-tabletop-toggle="${escapeHtml(parent.archetype_id)}">
          <span class="round-toggle">${open ? "−" : "+"}</span><span class="identity-label">${escapeHtml(parent.archetype_name)}</span></button>`
      : directIdentity
        ? `<button class="name-button" type="button" data-tabletop-detail="${escapeHtml(directIdentity)}">
            <span class="identity-label">${escapeHtml(parent.archetype_name)}</span></button>`
        : `<span class="identity-label">${escapeHtml(parent.archetype_name)}</span>`;
    const output = [tabletopRow({ ...parent, nameHtml }, "", advancementMetric)];
    if (!expandable && directIdentity && state.tabletopDetailIdentity === directIdentity) {
      output.push(tabletopDetailRow(directIdentity));
    }
    if (open) {
      subtypes.forEach(subtype => {
        const identityId = `${parent.archetype_id}/${subtype.subtype_id}`;
        output.push(tabletopRow({
          ...subtype,
          literal_record: overviewRecord(subtype.match_record?.all_matches),
          nameHtml: `<button class="name-button" type="button" data-tabletop-detail="${escapeHtml(identityId)}">
            <span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
        }, "subtype-row", advancementMetric));
        if (state.tabletopDetailIdentity === identityId) output.push(tabletopDetailRow(identityId));
      });
    }
    return output.join("");
  }).join("");
  const sortHeader = (label, key, tip) => {
    const arrow = state.tabletopSort === key ? (state.tabletopDirection === "desc" ? " ▼" : " ▲") : "";
    return `<button class="sort-button" type="button" data-tabletop-sort="${key}">${label}${arrow}</button>${tip ? infoTip(tip) : ""}`;
  };
  const advancementHeader = advancementMetric === "day2_conversion"
    ? sortHeader(
        t("tabletop.day2_conversion"),
        "day2_conversion",
        t("tabletop.day2_conversion_tip")
      )
    : sortHeader(t("tabletop.high_score_decks"), "high_score");
  return `<div class="panel-toolbar"><h2>${t("tabletop.overview_title")}</h2>
      <button id="tabletop-expand-all" class="secondary-button" type="button">${state.tabletopExpanded.size ? t("stats.hide_subtypes") : t("stats.show_subtypes")}</button>
    </div><div class="table-scroll"><table class="data-table metric-columns" style="width:1250px;min-width:100%">
      ${fixedColumns(9)}<thead><tr><th>${sortHeader(t("tabletop.deck_type"), "name")}</th><th class="number">${sortHeader(t("tabletop.deck_count"), "deck_count")}</th>
        <th class="number">${sortHeader(t("tabletop.metagame_share"), "metagame_share")}</th>
        <th class="number">${sortHeader(t("tabletop.average_points"), "average_points_per_effective_round", t("tabletop.average_points_tip"))}</th>
        <th class="number">${sortHeader(t("tabletop.win_rate"), "win_rate", t("tabletop.win_rate_tip"))}</th><th class="number">${t("tabletop.record")}</th>
        <th class="number">${sortHeader(t("tabletop.valid_matches"), "matches", t("tabletop.valid_matches_tip"))}</th>
        <th class="number">${sortHeader(t("tabletop.completion_rate"), "completion_rate", t("tabletop.completion_rate_tip"))}</th>
        <th class="number">${advancementHeader}</th></tr></thead>
      <tbody>${tabletopRow(tabletopOverall(scope, advancementMetric), "overall-row", advancementMetric)}${rows}</tbody>
    </table></div>`;
}

function tabletopMatchup(matchupDocument, scopeId, eventFormat) {
  const scope = matchupDocument.scopes[scopeId];
  const viewDocument = ReviewData.activeMatchupDocument({
    hierarchical: true,
    hierarchy: matchupDocument.hierarchy,
    parent_order: scope.parent_order,
    leaf_matrix: scope.leaf_matrix,
  }, LOW_SAMPLE_THRESHOLD);
  currentContext.matchupDisplayDocument = viewDocument;
  return `<div class="panel-toolbar"><div><h2>${t("tabletop.matchup_title")}</h2>
      <p class="matrix-toolbar-note">${t("tabletop.matchup_note", {
        scope: scopeLabel(scopeId, eventFormat),
        count: scope.included_match_count,
      })}</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? t("matchup.collapse_all") : t("matchup.expand_all")}</button>
    </div>${matchupLegend(viewDocument.min_sample_hint)}${matrixHtml(viewDocument)}`;
}

async function tabletopView() {
  const indexPath = productEntry().path;
  const {
    eventFormat,
    eventEntry,
    index,
    matchup,
    meta,
    mtgoDecks,
    overview,
    quality,
    tabletopDecks,
  } = await TabletopController.loadEvent(
    indexPath,
    state.tabletopEventId,
    state.format,
    MtgoController,
    {
      includeMatchup: state.tabletopView === "matchup",
      includeDecks: state.tabletopView === "overview"
        && Boolean(state.tabletopDetailIdentity),
    }
  );
  state.tabletopEventId = eventEntry.event_id;
  const catalogEventIds = new Set(index.events.map(item => item.event_id));
  state.tabletopSelectedEvents = new Set(
    [...state.tabletopSelectedEvents].filter(id => catalogEventIds.has(id))
  );
  if (!state.tabletopSelectedEvents.size) {
    state.tabletopSelectedEvents.add(eventEntry.event_id);
  }
  if (!state.tabletopLastSelectedEventId) {
    state.tabletopLastSelectedEventId = eventEntry.event_id;
  }
  const selectedEventIds = state.tabletopView === "matchup"
    ? [...state.tabletopSelectedEvents]
    : [eventEntry.event_id];
  const scopeState = TabletopController.resolveScopeState({
    events: index.events,
    selectedEventIds,
    activeEventId: eventEntry.event_id,
    requestedScope: state.tabletopScope,
    preferredSingleScope: state.tabletopLastScopeByEvent.get(eventEntry.event_id),
    restoreSingleScope: state.tabletopWasMultiEvent && selectedEventIds.length === 1,
  });
  state.tabletopScope = scopeState.scope;
  if (!scopeState.multi_event) {
    state.tabletopLastScopeByEvent.set(eventEntry.event_id, state.tabletopScope);
  }
  state.tabletopWasMultiEvent = scopeState.multi_event;
  const scope = overview.scopes[state.tabletopScope];
  const detailIdentities = new Set();
  scope.archetypes.forEach(parent => {
    const subtypes = activeTabletopSubtypes(parent);
    if (subtypes.length === 1) {
      detailIdentities.add(`${parent.archetype_id}/${subtypes[0].subtype_id}`);
    } else if (subtypes.length >= 2) {
      subtypes.forEach(subtype => {
        detailIdentities.add(`${parent.archetype_id}/${subtype.subtype_id}`);
      });
    } else if (parent.archetype_id) detailIdentities.add(parent.archetype_id);
  });
  if (
    state.tabletopDetailIdentity
    && !detailIdentities.has(state.tabletopDetailIdentity)
  ) {
    state.tabletopDetailIdentity = null;
  }
  const presentation = TabletopController.structurePresentation(overview);
  currentContext = {
    tabletopIndex: index,
    eventFormat,
    eventEntry,
    meta,
    overview,
    matchup,
    quality,
    tabletopDecks,
    mtgoDecks,
    scopeState,
  };
  const viewTabs = `<div class="tabletop-view-tabs subview-tabs" role="group" aria-label="${t("tabletop.view_label")}">
    <button type="button" data-tabletop-view="overview" class="${state.tabletopView === "overview" ? "active" : ""}">${t("tabletop.overview")}</button>
    <button type="button" data-tabletop-view="matchup" class="${state.tabletopView === "matchup" ? "active" : ""}">${t("tabletop.matchups")}</button>
  </div>`;
  const selector = state.tabletopView === "overview"
    ? `<div class="select-row"><label for="tabletop-event">${t("tabletop.select_event")}</label><select id="tabletop-event">${index.events.map(item => (
        `<option value="${escapeHtml(item.event_id)}" ${item.event_id === state.tabletopEventId ? "selected" : ""}>${escapeHtml(item.name)}</option>`
      )).join("")}</select></div>`
    : `<div class="select-row"><span>${t("tabletop.select_event")}</span><div class="event-selector-pane">${index.events.map(item => (
        `<label><input type="checkbox" data-tabletop-event-check="${escapeHtml(item.event_id)}"
          ${state.tabletopSelectedEvents.has(item.event_id) ? "checked" : ""}> ${escapeHtml(item.name)}</label>`
      )).join("")}</div></div>`;
  const disabledScopes = new Set(scopeState.disabled_scopes);
  const scopes = `<div class="range-buttons" aria-label="${t("tabletop.event_scope")}">${scopeState.scope_order.map(scopeId => (
    `<button type="button" data-tabletop-scope="${scopeId}" class="${state.tabletopScope === scopeId ? "active" : ""}"
      ${disabledScopes.has(scopeId) ? 'disabled aria-disabled="true"' : ""}>${scopeLabel(scopeId, eventFormat)}</button>`
  )).join("")}</div>`;
  const scopeLock = scopeState.multi_event
    ? `<p class="scope-lock-note">${t("tabletop.multi_scope_lock")}</p>`
    : "";
  const freshness = tabletopFreshness(
    scopeState, selectedEventIds, overview, scope, quality
  );
  const retainedQualityCodes = new Set([
    "disqualified_participant_matches_excluded",
  ]);
  if (presentation.show_mixed_selection_bias) {
    retainedQualityCodes.add("mixed_event_day2_selection_bias");
  }
  const issueList = quality.issues.filter(issue => retainedQualityCodes.has(issue.code)).map(issue => (
    issue.code === "disqualified_participant_matches_excluded"
      ? `<li>${t("tabletop.disqualified", {
        participants: quality.counts.disqualified_participant_count,
        matches: quality.counts.disqualified_matches_excluded,
      })}</li>`
      : `<li>${escapeHtml(issueMessage(issue, eventFormat))}</li>`
  )).join("");
  const eventSummary = scopeState.multi_event ? "" : `
    <section class="panel event-summary"><div class="event-title-row"><strong>${escapeHtml(overview.event.name)}</strong>
      <a href="${escapeHtml(overview.event.source_url)}" target="_blank" rel="noopener">${t("tabletop.source_event")}</a></div>
      <p>${escapeHtml(eventStructureLabel(overview.event_structure))} · ${t("tabletop.event_id", { id: escapeHtml(overview.event_id) })}</p>
      <div class="quality-notice"><strong>${t("tabletop.data_quality")}</strong>
        <ul class="quality-list">${issueList}</ul></div>
    </section>`;
  const content = scopeState.multi_event
    ? `<div class="empty-state">${t("tabletop.multi_event_pending", {
        count: selectedEventIds.length,
      })}</div>`
    : state.tabletopView === "overview"
      ? tabletopOverview(scope, presentation)
      : tabletopMatchup(matchup, state.tabletopScope, eventFormat);
  return `${viewTabs}${selector}${scopes}${scopeLock}${freshness}${eventSummary}
    <section class="panel">${content}</section>`;
}
