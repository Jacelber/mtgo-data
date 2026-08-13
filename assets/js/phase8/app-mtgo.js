"use strict";

const MANA_IDENTITIES = ArchetypeVisuals.manaIdentities;

function manaIdentityHtml(identityId) {
  const colors = MANA_IDENTITIES[state.format]?.[identityId];
  if (!colors?.length) return "";
  const names = colors.map(color => t(`mana.${color}`)).join(t("mana.separator"));
  return `<span class="mana-identity" aria-label="${escapeHtml(t("mana.identity", { colors: names }))}">
    ${colors.map(color => `<img src="assets/images/mana/${color}.svg" alt="">`).join("")}
  </span>`;
}

function locateDeck(decksDocument, identityId) {
  for (const value of Object.values(decksDocument.decks || {})) {
    if (value.archetype_id === identityId) {
      return value.subtypes?.length === 1 ? value.subtypes[0] : value;
    }
    const subtype = (value.subtypes || []).find(item => (
      `${item.parent_id}/${item.id}` === identityId
    ));
    if (subtype) return subtype;
  }
  return null;
}

function activeStatisticsSubtypes(parent) {
  return (parent.subtypes || []).filter(subtype => (
    Number(subtype.count) > 0
    || Number(subtype.high_score_count) > 0
    || Number(subtype.top8_count) > 0
    || Number.isFinite(subtype.avg_points_per_round)
  ));
}

function statisticsGroups(archetypes) {
  return archetypes.map(parent => {
    const subtypes = activeStatisticsSubtypes(parent);
    const expandable = subtypes.length >= 2;
    const open = expandable && state.statsExpanded.has(parent.id);
    const directId = subtypes.length === 1
      ? `${parent.id}/${subtypes[0].id}`
      : parent.id;
    return { parent, subtypes, expandable, open, directId };
  });
}

function statsRows(groups) {
  return groups.map(({ parent, subtypes, expandable, open, directId }) => {
    const parentIdentity = `${manaIdentityHtml(directId)}<span class="identity-label">${escapeHtml(parent.name)}</span>`;
    const parentName = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-stats-parent="${escapeHtml(parent.id)}"
          data-stats-toggle="${escapeHtml(parent.id)}" data-responsive-key="stats-action:${escapeHtml(parent.id)}"
          aria-expanded="${open}">
          <span class="round-toggle">${open ? "−" : "+"}</span>${parentIdentity}</button>`
      : `<button class="name-button" type="button" data-detail-identity="${escapeHtml(directId)}"
          data-responsive-key="stats-action:${escapeHtml(directId)}" aria-expanded="${state.detailIdentity === directId}"
          data-stats-parent="${escapeHtml(parent.id)}">
          ${parentIdentity}</button>`;
    const rows = [statsRow(parent, parentName, "")];
    if (state.detailIdentity === parent.id) rows.push(statsDetailRow(parent.id));
    else if (!expandable && state.detailIdentity === directId) rows.push(statsDetailRow(directId));
    if (open) {
      subtypes.forEach(subtype => {
        const identityId = `${parent.id}/${subtype.id}`;
        rows.push(statsRow(
          subtype,
          `<button class="name-button" type="button" data-detail-identity="${escapeHtml(identityId)}"
            data-responsive-key="stats-action:${escapeHtml(identityId)}" aria-expanded="${state.detailIdentity === identityId}">
            ${manaIdentityHtml(identityId)}<span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
          "subtype-row"
        ));
        if (state.detailIdentity === identityId) rows.push(statsDetailRow(identityId));
      });
    }
    return rows.join("");
  }).join("");
}

function statsRow(record, nameHtml, rowClass) {
  return `<tr class="${rowClass}">
    <td class="identity-cell">${nameHtml}</td>
    <td class="number">${number(record.avg_points_per_round)}</td>
    <td class="number">${record.high_score_count ?? 0}</td>
    <td class="number">${pct(record.high_score_share)}</td>
    <td class="number">${record.top8_count ?? 0}</td>
    <td class="number">${pct(record.top8_share)}</td>
    <td class="number">${pct(record.conversion)}</td>
  </tr>`;
}

function chartHtml(archetypes) {
  const sorted = [...archetypes]
    .sort((a, b) => (Number(b.high_score_share) || 0) - (Number(a.high_score_share) || 0));
  const known = sorted.filter(item => item.id !== "unknown");
  const unknown = sorted.find(item => item.id === "unknown");
  const visible = known.filter(item => Number(item.high_score_share) >= 0.03);
  const remainder = known.filter(item => Number(item.high_score_share) < 0.03)
    .reduce((sum, item) => sum + (Number(item.high_score_share) || 0), 0);
  const segments = visible.map((item, index) => ({
    id: item.id,
    name: item.name,
    share: Number(item.high_score_share) || 0,
    color: `composition-color-${index % 6 + 1}`,
    image: REPRESENTATIVE_CARDS[state.format]?.[item.id]?.[0]?.image,
  }));
  if (remainder > 0) {
    segments.push({ name: t("chart.other"), share: remainder, color: "other" });
  }
  if (Number(unknown?.high_score_share) > 0) {
    segments.push({ name: t("chart.unknown"), share: Number(unknown.high_score_share), color: "unknown" });
  }
  const assigned = segments.reduce((sum, item) => sum + item.share, 0);
  if (assigned < 0.99999) {
    segments.push({
      name: t("chart.unassigned"),
      share: Math.max(0, 1 - assigned),
      color: "unassigned",
    });
  }
  const bar = segments.map(item => {
    const value = pct(item.share);
    const detail = `${item.name} · ${value}`;
    const className = `composition-segment ${item.color}${item.image ? " has-card-art" : ""}${state.detailIdentity === item.id ? " selected" : ""}`;
    const style = `--composition-share:${(item.share * 100).toFixed(6)}%${item.image ? `;--composition-image:url(${item.image})` : ""}`;
    return accessibleCompositionSegment({
      className,
      style,
      label: detail,
      identity: item.id,
      expanded: state.detailIdentity === item.id,
    });
  }).join("");
  return `<section class="panel composition-panel" aria-label="${t("chart.aria")}">
    <div class="composition-heading"><div><h2>${t("chart.title")}</h2><small>${t("chart.threshold")}</small></div>
      <p><span class="desktop-instruction">${t("chart.desktop_instruction")}</span><span class="mobile-instruction">${t("chart.mobile_instruction")}</span></p></div>
    <div class="composition-bar">${bar}</div>
    <p class="composition-note">${t("chart.description")}</p>
  </section>`;
}

function sortedArchetypes(archetypes) {
  const direction = state.statsDirection === "asc" ? 1 : -1;
  return [...archetypes].sort((left, right) => {
    const a = state.statsSort === "name" ? left.name.toLowerCase() : (left[state.statsSort] ?? -1);
    const b = state.statsSort === "name" ? right.name.toLowerCase() : (right[state.statsSort] ?? -1);
    return a < b ? -direction : a > b ? direction : 0;
  });
}

async function statsView() {
  const { meta, range, decks, completeness } = await MtgoController
    .loadStatistics(state.format, state.statsRange, {
      includeDecks: Boolean(state.detailIdentity),
    });
  const archetypes = sortedArchetypes(range.archetypes);
  const identityNames = new Map();
  const detailIdentities = new Set();
  range.archetypes.forEach(parent => {
    identityNames.set(parent.id, parent.name);
    const subtypes = activeStatisticsSubtypes(parent);
    subtypes.forEach(subtype => identityNames.set(`${parent.id}/${subtype.id}`, subtype.display_name));
    detailIdentities.add(parent.id);
    if (subtypes.length === 1) detailIdentities.add(`${parent.id}/${subtypes[0].id}`);
    else if (subtypes.length >= 2) {
      subtypes.forEach(subtype => detailIdentities.add(`${parent.id}/${subtype.id}`));
    }
  });
  if (state.detailIdentity && !detailIdentities.has(state.detailIdentity)) {
    state.detailIdentity = null;
  }
  currentContext = { meta, range, decks, completeness, identityNames };
  const groups = statisticsGroups(archetypes);
  const expandable = groups.filter(item => item.expandable);
  const sortHeader = (label, key, tip) => {
    const arrow = state.statsSort === key ? (state.statsDirection === "desc" ? "▼" : "▲") : "";
    const accessories = `${arrow ? `<span class="sort-indicator" aria-hidden="true">${arrow}</span>` : ""}${tip ? infoTip(tip) : ""}`;
    return `<button class="sort-button" type="button" data-stats-sort="${key}" data-responsive-key="stats-sort-field:${escapeHtml(key)}">
      <span class="sort-label">${label}</span></button>${accessories ? `<span class="sort-accessories">${accessories}</span>` : ""}`;
  };
  const sortOptions = [
    ["name", t("stats.deck")],
    ["avg_points_per_round", t("stats.average_points")],
    ["high_score_count", t("stats.high_count")],
    ["high_score_share", t("stats.high_share")],
    ["top8_count", t("stats.top8_count")],
    ["top8_share", t("stats.top8_share")],
    ["conversion", t("stats.conversion")],
  ].map(([key, label]) => ({ key, label }));
  return `<aside class="source-note" aria-label="${t("source.label")}">
      <p>${t("source.stats")}</p>
    </aside>
    ${rangeButtons(state.statsRange, "data-stats-range")}
    ${statisticsFreshness(meta, range, completeness)}
    ${chartHtml(archetypes)}
    <section class="panel">
      <div class="panel-toolbar"><h2>${t("stats.title")}</h2>
        ${expandable.length ? `<button id="stats-expand-all" class="secondary-button" type="button">${state.statsExpanded.size ? t("stats.hide_subtypes") : t("stats.show_subtypes")}</button>` : ""}
      </div>
      <p class="real-data-note">${t("stats.note")}</p>
      <div class="desktop-metric-table table-scroll"><table class="data-table metric-columns" style="width:980px;min-width:100%">
        ${fixedColumns(7)}
        <thead><tr><th>${sortHeader(t("stats.deck"), "name")}</th>
          <th class="number">${sortHeader(t("stats.average_points"), "avg_points_per_round", t("stats.average_points_tip"))}</th>
          <th class="number">${sortHeader(t("stats.high_count"), "high_score_count")}</th>
          <th class="number">${sortHeader(t("stats.high_share"), "high_score_share")}</th>
          <th class="number">${sortHeader(t("stats.top8_count"), "top8_count")}</th>
          <th class="number">${sortHeader(t("stats.top8_share"), "top8_share")}</th>
          <th class="number">${sortHeader(t("stats.conversion"), "conversion", t("stats.conversion_tip"))}</th>
        </tr></thead><tbody>${statsRows(groups)}</tbody>
      </table></div>
      <div class="mobile-metric-layout">
        ${mobileSortControls({
          kind: "stats",
          current: state.statsSort,
          direction: state.statsDirection,
          options: sortOptions,
        })}
        ${statsCards(groups)}
      </div>
    </section>`;
}

function matchupLegend(lowSampleThreshold) {
  const lowSampleText = Number.isFinite(lowSampleThreshold)
    ? t("matchup.low_sample", { count: lowSampleThreshold })
    : t("matchup.threshold_pending");
  return `<div class="matchup-legend">
    <span>${t("matchup.colors")}</span><div><div class="legend-bar"></div>
      <div class="legend-values"><span>0%</span><span>50%</span><span>100%</span></div></div>
    <span><i class="na-chip"></i>${t("matchup.none")}</span><span><i class="low-chip"></i>${lowSampleText}</span>
  </div>`;
}

function mixColor(from, to, ratio) {
  const channel = index => Math.round(from[index] + (to[index] - from[index]) * ratio);
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

function winRateColor(rate) {
  const red = [191, 86, 76];
  const yellow = [232, 200, 74];
  const green = [57, 137, 87];
  return rate <= 0.5
    ? mixColor(red, yellow, Math.max(0, rate) * 2)
    : mixColor(yellow, green, Math.min(1, (rate - 0.5) * 2));
}

function matrixCell(record) {
  if (!record || record.win_rate === null) return `<td class="matrix-cell na" title="${t("matchup.none")}">—</td>`;
  const low = record.low_sample ? "low-sample" : "";
  const ci = record.confidence_interval_95;
  const half = ci ? ((ci.upper - ci.lower) / 2) : null;
  const recordText = `${record.wins}-${record.losses}-${record.draws}（${record.matches}）`;
  const foreground = record.win_rate < 0.2 || record.win_rate > 0.72 ? "#fff" : "#26313a";
  return `<td class="matrix-cell ${low}" tabindex="0"
    style="background:${winRateColor(record.win_rate)};color:${foreground}"
    data-record="${recordText}" title="${t("matchup.record", { record: recordText })}${record.mirror ? ` · ${t("matchup.mirror")}` : ""}">
    <strong>${(record.win_rate * 100).toFixed(1)}</strong><small>${half === null ? "—" : `±${(half * 100).toFixed(1)}`}</small></td>`;
}

function matrixHtml(document) {
  const view = ReviewData.buildView(document, state.matchupRows, state.matchupColumns);
  const table = `<table class="matchup-table">
    <thead><tr><th class="corner"></th><th class="column-head overall">${t("matchup.overall")}</th>
      ${view.columns.map(column => {
        const open = state.matchupColumns.has(column.parentId);
        const content = column.kind === "archetype" && column.expandable
          ? `<button type="button" class="axis-label-button column-axis-label" data-matchup-column="${escapeHtml(column.parentId)}"
              aria-label="${open ? t("matchup.collapse") : t("matchup.expand")}${escapeHtml(column.name)}" title="${escapeHtml(column.name)}">
              <span class="axis-toggle">${open ? "−" : "+"}</span><span class="axis-name">${escapeHtml(column.name)}</span></button>`
          : `<span>${escapeHtml(column.name)}</span>`;
        return `<th class="column-head ${column.kind === "subtype" ? "subtype-head" : ""}"><div>${content}</div></th>`;
      }).join("")}
    </tr></thead><tbody>
      ${view.rows.map(row => {
        const open = state.matchupRows.has(row.parentId);
        const content = row.kind === "archetype" && row.expandable
          ? `<button type="button" class="axis-label-button row-axis-label" data-matchup-row="${escapeHtml(row.parentId)}"
              aria-label="${open ? t("matchup.collapse") : t("matchup.expand")}${escapeHtml(row.name)}">
              <span class="axis-toggle">${open ? "−" : "+"}</span><span class="row-axis-name" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</span></button>`
          : `<span class="row-axis-name" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</span>`;
        return `<tr><th class="row-head ${row.kind === "subtype" ? "subtype-head" : ""}">${content}</th>
          ${matrixCell(view.overall[row.id])}${view.columns.map(column => matrixCell(view.matrix[row.id][column.id])).join("")}</tr>`;
      }).join("")}
    </tbody></table>`;
  return `${horizontalScrollFrame("matchup", "table-scroll matrix-scroll", table, matrixStickyHeader(view.columns))}<div id="matrix-record" class="matrix-record" role="status" hidden></div>
    <div id="matrix-hover-pop" class="matrix-hover-pop" role="tooltip" hidden></div>`;
}

async function matchupView() {
  const { document, completeness } = await MtgoController
    .loadMatchup(state.format, state.matchupRange);
  const displayDocument = ReviewData.activeMatchupDocument(document, LOW_SAMPLE_THRESHOLD);
  currentContext = { matchupDocument: displayDocument, completeness };
  return `${rangeButtons(state.matchupRange, "data-matchup-range")}
    <aside class="source-note" aria-label="${t("source.label")}">
      <p>${t("source.matchups")}</p>
    </aside>
    ${matchupFreshness(completeness)}
    <section class="panel"><div class="panel-toolbar"><div><h2>${t("matchup.title")}</h2>
      <p class="matrix-toolbar-note">${t("matchup.note")}</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? t("matchup.collapse_all") : t("matchup.expand_all")}</button>
    </div>${matchupLegend(displayDocument.min_sample_hint)}${matrixHtml(displayDocument)}</section>`;
}

function top8PlacementDetail() {
  if (!state.top8Detail) return "";
  const [eventId, rankText] = state.top8Detail.split(":");
  const event = currentContext.top8.events.find(item => item.event_id === eventId);
  const placement = event?.placements.find(item => item.rank === Number(rankText));
  if (!placement) return "";
  const identityId = placement.identity?.identity_id;
  const base = currentContext.bases.identities?.[identityId];
  return deckDetailHtml({
    title: placement.identity?.display_name || t("top8.unknown"),
    exactDeck: placement.exact_deck,
    averageDeck: base?.average_deck,
    comparison: { ...placement.comparison, rank: placement.rank, date: event.date },
    closeAction: "data-close-top8",
  });
}

async function top8View() {
  const indexPath = productEntry().path;
  const { index, weekEntry, top8, bases } = await MtgoController
    .loadTop8(indexPath, state.top8WeekFile, {
      includeBases: Boolean(state.top8Detail),
    });
  state.top8WeekFile = weekEntry.file;
  const availableDetails = new Set(top8.events.flatMap(event => (
    event.placements
      .filter(placement => placement.deck_status === "available")
      .map(placement => `${event.event_id}:${placement.rank}`)
  )));
  if (state.top8Detail && !availableDetails.has(state.top8Detail)) {
    state.top8Detail = null;
  }
  currentContext = { top8Index: index, top8, bases };
  return `<aside class="source-note" aria-label="${t("source.label")}"><p>${t("source.top8")}</p></aside>
    <div class="select-row"><label for="top8-week">${t("top8.week")}</label>
      <select id="top8-week">${index.weeks.map(item => (
        `<option value="${escapeHtml(item.file)}" ${item.file === state.top8WeekFile ? "selected" : ""}>${item.start} ～ ${item.end}</option>`
      )).join("")}</select>
    </div>
    ${top8Freshness(top8, weekEntry)}
    <section class="panel"><h2 class="sr-only">${t("top8.title")}</h2>
      ${horizontalScrollFrame("top8", "table-scroll", `<table class="top8-table top8-week-table"><thead><tr><th>${t("top8.rank")}</th>
        ${top8.events.map(event => `<th title="${escapeHtml(event.name)}"><strong>${escapeHtml(event.display_name)}</strong>
          <small>${event.date} · ${t("top8.players", { count: event.player_count })}</small></th>`).join("")}
      </tr></thead><tbody>${Array.from({ length: 8 }, (_, offset) => {
        const rank = offset + 1;
        return `<tr><td>${rank}</td>${top8.events.map(event => {
          const placement = event.placements.find(item => item.rank === rank);
          if (!placement || placement.deck_status !== "available") return `<td class="missing-deck">${t("top8.unavailable")}</td>`;
          const detailId = `${event.event_id}:${rank}`;
          return `<td><button class="name-button" type="button" data-top8-detail="${escapeHtml(detailId)}"
            aria-expanded="${state.top8Detail === detailId}">${escapeHtml(placement.identity.display_name)}</button></td>`;
        }).join("")}</tr>`;
      }).join("")}</tbody></table>`)}${top8PlacementDetail()}</section>`;
}

function pickupDeck(item, key) {
  const title = key === "existing_changes"
    ? t("pickup.new_tech")
    : t("pickup.new_decks");
  const id = `${key}:${item.archetype}:${item.player}`;
  const open = state.pickupOpen.has(id);
  const comment = I18n.language() === "en"
    ? (item.comment_en || item.comment_zh || "")
    : (item.comment_zh || "");
  return `<article class="pickup-card ${open ? "open" : ""}">
    <button type="button" class="pickup-head" data-pickup-toggle="${escapeHtml(id)}" aria-expanded="${open}">
      <span><strong>${escapeHtml(item.archetype)}</strong><small>${escapeHtml(item.player)} · ${t("deck.rank")} ${item.final_rank}
      · ${t("deck.points", { count: item.swiss_score })} · ${dateText(item.starttime)}</small></span><b>${title} · ${t("deck.deviation")} ${t("deck.points", { count: item.deviation })}</b>
    </button>${open ? `<div class="pickup-body"><p>${escapeHtml(comment)}</p>
      <div class="deck-columns"><div class="deck-column"><h4>${t("deck.main")}</h4>${cardList(item.main_deck)}</div>
      <div class="deck-column"><h4>${t("deck.side")}</h4>${cardList(item.side_deck)}</div></div></div>` : ""}</article>`;
}

async function pickupView() {
  const indexPath = productEntry().path;
  const { index, week, document } = await MtgoController
    .loadPickup(indexPath, state.pickupWeekFile);
  state.pickupWeekFile = week.file;
  currentContext = { pickupIndex: index, pickupDocument: document };
  const groups = [
    [t("pickup.new_tech"), "existing_changes"],
    [t("pickup.new_decks"), "new_archetypes"],
  ];
  return `<aside class="source-note" aria-label="${t("source.label")}"><p>${t("source.pickup")}</p></aside>
    ${pickupFreshness(week, document)}
    <div class="pickup-layout"><aside class="pickup-weeks"><h2>${t("pickup.archive")}</h2>${index.weeks.map(item => (
      `<button type="button" data-pickup-week="${escapeHtml(item.file)}" class="${item.file === state.pickupWeekFile ? "active" : ""}">
        ${escapeHtml(item.week)}<span>${item.start} ～ ${item.end}</span></button>`
    )).join("")}</aside><div class="pickup-content">${groups.map(([title, key]) => (
      `<section class="pickup-group"><h2>${title}</h2>${document[key]?.length
        ? document[key].map(item => pickupDeck(item, key)).join("")
        : `<p class="pickup-empty">${t("pickup.empty")}</p>`}</section>`
    )).join("")}</div></div>`;
}
