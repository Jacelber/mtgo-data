"use strict";

function mobileMetricHtml(label, value, className = "") {
  return `<div class="mobile-metric ${className}">
    <dt>${label}</dt><dd>${value}</dd>
  </div>`;
}

function mobileSortControls({ kind, current, direction, options }) {
  const id = `${kind}-mobile-sort`;
  const dataSelect = kind === "stats" ? "data-mobile-stats-sort" : "data-mobile-tabletop-sort";
  const dataDirection = kind === "stats" ? "data-mobile-stats-direction" : "data-mobile-tabletop-direction";
  const directionLabel = direction === "asc" ? t("mobile.ascending") : t("mobile.descending");
  const targetLabel = direction === "asc" ? t("mobile.switch_descending") : t("mobile.switch_ascending");
  return `<div class="mobile-sort-controls">
    <label for="${id}">${t("mobile.sort_by")}</label>
    <select id="${id}" ${dataSelect} data-responsive-key="${kind}-sort-field:${escapeHtml(current)}">
      ${options.map(option => `<option value="${escapeHtml(option.key)}" ${option.key === current ? "selected" : ""}>${option.label}</option>`).join("")}
    </select>
    <button type="button" class="mobile-sort-direction" ${dataDirection}
      data-responsive-key="${kind}-sort-direction" aria-label="${escapeHtml(targetLabel)}">
      <span aria-hidden="true">${direction === "asc" ? "↑" : "↓"}</span>${directionLabel}
    </button>
  </div>`;
}

function scrollHintKey(kind) {
  const view = state.product === "tabletop-major-events" ? state.tabletopView : state.product;
  return `${state.format}:${view}:${kind}`;
}

function horizontalScrollFrame(kind, className, content, stickyContent = "") {
  const key = scrollHintKey(kind);
  const dismissed = state.scrollHintsSeen.has(key) ? " hint-dismissed" : "";
  return `<div class="horizontal-scroll-frame${dismissed}" data-scroll-frame="${escapeHtml(key)}">
    <p class="horizontal-scroll-hint">${t("mobile.scroll_hint")}</p>
    ${stickyContent}
    <div class="${className}" data-scroll-hint-key="${escapeHtml(key)}">${content}</div>
  </div>`;
}

function matrixStickyHeader(columns) {
  return `<div class="matrix-sticky-header" data-matrix-sticky>
    <div class="matrix-sticky-viewport">
      <table class="matrix-sticky-table" aria-hidden="true"><thead><tr>
        <th class="corner"></th><th class="column-head overall">${t("matchup.overall")}</th>
        ${columns.map(column => `<th class="column-head ${column.kind === "subtype" ? "subtype-head" : ""}">
          <div class="column-axis-controls"><span class="axis-name">${escapeHtml(column.name)}</span></div></th>`).join("")}
      </tr></thead></table>
    </div>
  </div>`;
}

function statsDetailRow(identityId) {
  return `<tr class="deck-detail-row"><td colspan="7">${statsDeckDetail(identityId, {
    responsiveKey: `stats-detail:${identityId}`,
  })}</td></tr>`;
}

function statsDeckDetail(identityId, options = {}) {
  const record = locateDeck(currentContext.decks, identityId);
  const title = record?.display_name || record?.name || currentContext.identityNames?.get(identityId) || identityId;
  return deckDetailHtml({
    title,
    bestDeck: record?.best_deck,
    averageDeck: record?.average_deck,
    closeAction: "data-close-detail",
    ...options,
  });
}

function statsMobileDetail(identityId) {
  return `<div id="stats-mobile-detail-${escapeHtml(identityId)}" class="mobile-card-detail"
    data-mobile-expanded-content="stats:${escapeHtml(identityId)}">${statsDeckDetail(identityId, {
      closeAction: "data-close-mobile-stats-detail",
      className: "mobile-deck-detail",
      responsiveKey: `stats-detail:${identityId}`,
    })}</div>`;
}

function statsMobileCard(record, {
  identityId,
  parentId,
  displayName,
  expandable = false,
  open = false,
  subtype = false,
}) {
  const detailOpen = state.detailIdentity === identityId;
  const titleId = `stats-mobile-title-${identityId}`;
  const action = expandable
    ? `<button type="button" class="mobile-card-action" data-mobile-stats-toggle="${escapeHtml(parentId)}"
        data-responsive-key="stats-action:${escapeHtml(parentId)}" aria-expanded="${open}"
        aria-controls="stats-mobile-subtypes-${escapeHtml(parentId)}">
        ${open ? t("mobile.collapse_subtypes") : t("mobile.expand_subtypes")}</button>`
    : `<button type="button" class="mobile-card-action" data-mobile-stats-detail="${escapeHtml(identityId)}"
        data-responsive-key="stats-action:${escapeHtml(identityId)}" aria-expanded="${detailOpen}"
        aria-controls="stats-mobile-detail-${escapeHtml(identityId)}">
        ${detailOpen ? t("mobile.close_deck") : t("mobile.view_deck")}</button>`;
  return `<article class="mobile-metric-card${subtype ? " subtype-card" : ""}${detailOpen ? " detail-open" : ""}"
      data-mobile-card-identity="${escapeHtml(identityId)}"
      role="listitem" aria-labelledby="${escapeHtml(titleId)}">
    <div class="mobile-card-heading">
      <div class="mobile-card-title">${manaIdentityHtml(identityId)}<div>
        ${subtype ? `<span class="mobile-subtype-label">${t("mobile.subtype")}</span>` : ""}
        <h3 id="${escapeHtml(titleId)}">${escapeHtml(displayName)}</h3></div></div>
      ${action}
    </div>
    <dl class="mobile-primary-metrics">
      ${mobileMetricHtml(t("stats.high_share"), pct(record.high_score_share), "hero-metric")}
      ${mobileMetricHtml(t("stats.average_points"), number(record.avg_points_per_round))}
      ${mobileMetricHtml(t("stats.top8_share"), pct(record.top8_share))}
    </dl>
    <dl class="mobile-secondary-metrics">
      ${mobileMetricHtml(t("stats.high_count"), record.high_score_count ?? 0)}
      ${mobileMetricHtml(t("stats.top8_count"), record.top8_count ?? 0)}
      ${mobileMetricHtml(t("stats.conversion"), pct(record.conversion))}
    </dl>
    ${detailOpen ? statsMobileDetail(identityId) : ""}
  </article>`;
}

function statsCards(groups) {
  return `<div class="mobile-metric-list" role="list">${groups.map(group => {
    const parentCard = statsMobileCard(group.parent, {
      identityId: group.directId,
      parentId: group.parent.id,
      displayName: group.parent.name,
      expandable: group.expandable,
      open: group.open,
    });
    const subtypeCards = group.open
      ? `<div id="stats-mobile-subtypes-${escapeHtml(group.parent.id)}" class="mobile-subtype-list"
          data-mobile-expanded-content="stats-subtypes:${escapeHtml(group.parent.id)}">${group.subtypes.map(subtype => {
          const identityId = `${group.parent.id}/${subtype.id}`;
          return statsMobileCard(subtype, {
            identityId,
            parentId: group.parent.id,
            displayName: subtype.display_name,
            subtype: true,
          });
        }).join("")}</div>`
      : "";
    return `<div class="mobile-metric-group">${parentCard}${subtypeCards}</div>`;
  }).join("")}</div>`;
}

function tabletopMobileDetail(identityId) {
  return `<div id="tabletop-mobile-detail-${escapeHtml(identityId)}" class="mobile-card-detail"
    data-mobile-expanded-content="tabletop:${escapeHtml(identityId)}">${tabletopDeckDetail(identityId, {
      closeAction: "data-close-mobile-tabletop-detail",
      className: "mobile-deck-detail",
      responsiveKey: `tabletop-detail:${identityId}`,
    })}</div>`;
}

function tabletopMobileCard(record, {
  identityId,
  parentId,
  displayName,
  advancementMetric,
  expandable = false,
  open = false,
  subtype = false,
  overall = false,
}) {
  const match = record.literal_record || overviewRecord(record.match_record?.all_matches);
  const detailOpen = Boolean(identityId)
    && !overall
    && state.tabletopDetailIdentity === identityId;
  const titleId = `tabletop-mobile-title-${identityId}`;
  const action = overall || !identityId
    ? ""
    : expandable
      ? `<button type="button" class="mobile-card-action" data-mobile-tabletop-toggle="${escapeHtml(parentId)}"
          data-responsive-key="tabletop-action:${escapeHtml(parentId)}" aria-expanded="${open}"
          aria-controls="tabletop-mobile-subtypes-${escapeHtml(parentId)}">
          ${open ? t("mobile.collapse_subtypes") : t("mobile.expand_subtypes")}</button>`
      : `<button type="button" class="mobile-card-action" data-mobile-tabletop-detail="${escapeHtml(identityId)}"
          data-responsive-key="tabletop-action:${escapeHtml(identityId)}" aria-expanded="${detailOpen}"
          aria-controls="tabletop-mobile-detail-${escapeHtml(identityId)}">
          ${detailOpen ? t("mobile.close_deck") : t("mobile.view_deck")}</button>`;
  const advancementLabel = advancementMetric === "day2_conversion"
    ? t("tabletop.day2_conversion")
    : t("tabletop.high_score_decks");
  const advancementValue = advancementMetric === "day2_conversion"
    ? pct(record.day2_conversion)
    : (record.high_score?.count ?? "—");
  return `<article class="mobile-metric-card${subtype ? " subtype-card" : ""}${overall ? " overall-card" : ""}${detailOpen ? " detail-open" : ""}"
      role="listitem" aria-labelledby="${escapeHtml(titleId)}">
    <div class="mobile-card-heading">
      <div class="mobile-card-title"><div>
        ${subtype ? `<span class="mobile-subtype-label">${t("mobile.subtype")}</span>` : ""}
        <h3 id="${escapeHtml(titleId)}">${escapeHtml(displayName)}</h3></div></div>
      ${action}
    </div>
    <dl class="mobile-primary-metrics">
      ${mobileMetricHtml(t("tabletop.metagame_share"), `${pct(record.metagame_share)}<small>${record.deck_count} ${t("tabletop.deck_count")}</small>`, "hero-metric")}
      ${mobileMetricHtml(t("tabletop.average_points"), number(record.average_points_per_effective_round))}
      ${mobileMetricHtml(t("tabletop.win_rate"), `${pct(match?.win_rate)}<small>${match?.matches ?? "—"} ${t("tabletop.valid_matches")}</small>`)}
    </dl>
    <dl class="mobile-secondary-metrics">
      ${mobileMetricHtml(t("tabletop.record"), match ? `${match.wins}-${match.losses}-${match.draws}` : "—")}
      ${mobileMetricHtml(t("tabletop.completion_rate"), pct(record.completion_rate))}
      ${mobileMetricHtml(advancementLabel, advancementValue)}
    </dl>
    ${detailOpen ? tabletopMobileDetail(identityId) : ""}
  </article>`;
}

function tabletopCards(groups, overall, advancementMetric) {
  const overallCard = tabletopMobileCard(overall, {
    identityId: "overall",
    displayName: overall.name,
    advancementMetric,
    overall: true,
  });
  return `<div class="mobile-metric-list" role="list">${overallCard}${groups.map(group => {
    const parentCard = tabletopMobileCard(group.parent, {
      identityId: group.directIdentity,
      parentId: group.parent.archetype_id,
      displayName: group.parent.archetype_name,
      advancementMetric,
      expandable: group.expandable,
      open: group.open,
    });
    const subtypeCards = group.open
      ? `<div id="tabletop-mobile-subtypes-${escapeHtml(group.parent.archetype_id)}" class="mobile-subtype-list"
          data-mobile-expanded-content="tabletop-subtypes:${escapeHtml(group.parent.archetype_id)}">${group.subtypes.map(subtype => {
          const identityId = `${group.parent.archetype_id}/${subtype.subtype_id}`;
          return tabletopMobileCard({
            ...subtype,
            literal_record: overviewRecord(subtype.match_record?.all_matches),
          }, {
            identityId,
            parentId: group.parent.archetype_id,
            displayName: subtype.display_name,
            advancementMetric,
            subtype: true,
          });
        }).join("")}</div>`
      : "";
    return `<div class="mobile-metric-group">${parentCard}${subtypeCards}</div>`;
  }).join("")}</div>`;
}
