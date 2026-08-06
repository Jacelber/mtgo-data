"use strict";

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

function statsRows(archetypes) {
  return archetypes.map(parent => {
    const subtypes = activeStatisticsSubtypes(parent);
    const expandable = subtypes.length >= 2;
    const open = expandable && state.statsExpanded.has(parent.id);
    const directId = subtypes.length === 1
      ? `${parent.id}/${subtypes[0].id}`
      : parent.id;
    const parentName = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-stats-toggle="${escapeHtml(parent.id)}">
          <span class="round-toggle">${open ? "−" : "+"}</span><span class="identity-label">${escapeHtml(parent.name)}</span></button>`
      : `<button class="name-button" type="button" data-detail-identity="${escapeHtml(directId)}">
          <span class="identity-label">${escapeHtml(parent.name)}</span></button>`;
    const rows = [statsRow(parent, parentName, "")];
    if (!expandable && state.detailIdentity === directId) rows.push(statsDetailRow(directId));
    if (open) {
      subtypes.forEach(subtype => {
        const identityId = `${parent.id}/${subtype.id}`;
        rows.push(statsRow(
          subtype,
          `<button class="name-button" type="button" data-detail-identity="${escapeHtml(identityId)}">
            <span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
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

function statsDetailRow(identityId) {
  const record = locateDeck(currentContext.decks, identityId);
  const title = record?.display_name || record?.name || currentContext.identityNames?.get(identityId) || identityId;
  return `<tr class="deck-detail-row"><td colspan="7">${deckDetailHtml({
    title,
    bestDeck: record?.best_deck,
    averageDeck: record?.average_deck,
    closeAction: "data-close-detail",
  })}</td></tr>`;
}

function piePoint(percent, radius = 88) {
  const angle = (percent * 3.6 - 90) * Math.PI / 180;
  return {
    x: 100 + radius * Math.cos(angle),
    y: 100 + radius * Math.sin(angle),
  };
}

function piePath(startPercent, endPercent) {
  const start = piePoint(startPercent);
  const end = piePoint(endPercent >= 100 ? 99.9999 : endPercent);
  const largeArc = endPercent - startPercent > 50 ? 1 : 0;
  return `M 100 100 L ${start.x.toFixed(3)} ${start.y.toFixed(3)}
    A 88 88 0 ${largeArc} 1 ${end.x.toFixed(3)} ${end.y.toFixed(3)} Z`;
}

function pieChart(archetypes, key, label) {
  const countKey = key === "high_score_share" ? "high_score_count" : "top8_count";
  const sorted = [...archetypes].sort((a, b) => (b[key] || 0) - (a[key] || 0));
  const visible = sorted.filter(item => Number(item[key]) > 0.02);
  const remainder = sorted.filter(item => Number(item[key]) <= 0.02)
    .reduce((sum, item) => sum + (Number(item[key]) || 0), 0);
  const remainderCount = sorted.filter(item => Number(item[key]) <= 0.02)
    .reduce((sum, item) => sum + (Number(item[countKey]) || 0), 0);
  const slices = remainder > 0
    ? [...visible, { name: t("chart.other"), [key]: remainder, [countKey]: remainderCount, other: true }]
    : visible;
  let cursor = 0;
  const segments = slices.map((item, index) => {
    const start = cursor;
    cursor += (Number(item[key]) || 0) * 100;
    const color = item.other ? "#c7ccd1" : PIE_COLORS[index % PIE_COLORS.length];
    const detail = `${item.name} · ${pct(item[key])} · ${t("chart.decks", { count: Number(item[countKey]) || 0 })}`;
    return `<path class="pie-slice" d="${piePath(start, cursor)}" fill="${color}"
      tabindex="0" data-pie-detail="${escapeHtml(detail)}" aria-label="${escapeHtml(detail)}">
      <title>${escapeHtml(detail)}</title></path>`;
  });
  if (cursor < 99.999) {
    segments.push(`<path class="pie-slice pie-slice-unavailable" d="${piePath(cursor, 100)}" fill="#eef0f2"
      tabindex="0" data-pie-detail="${t("chart.unassigned")} · ${(100 - cursor).toFixed(1)}% · ${t("chart.decks", { count: 0 })}"
      aria-label="${t("chart.unassigned")} · ${(100 - cursor).toFixed(1)}% · ${t("chart.decks", { count: 0 })}"></path>`);
  }
  const legend = slices.map((item, index) => (
    `<li><i style="background:${item.other ? "#c7ccd1" : PIE_COLORS[index % PIE_COLORS.length]}"></i>
      <span>${escapeHtml(item.name)}</span><strong>${pct(item[key])}</strong>
      <small>${t("chart.count", { count: Number(item[countKey]) || 0 })}</small></li>`
  )).join("");
  return `<article class="pie-card"><h3>${label}</h3><div class="pie-body">
    <div class="pie-chart-shell"><svg class="pie" viewBox="0 0 200 200" role="img" aria-label="${label}">
      ${segments.join("")}</svg>
      <div class="pie-readout" role="status">${t("chart.help")}</div></div>
    <ul class="pie-legend">${legend}</ul></div></article>`;
}

function chartHtml(archetypes) {
  return `<section class="panel pie-panel" aria-label="${t("chart.aria")}">
    ${pieChart(archetypes, "high_score_share", t("stats.high_share"))}
    ${pieChart(archetypes, "top8_share", t("stats.top8_share"))}
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
  range.archetypes.forEach(parent => {
    identityNames.set(parent.id, parent.name);
    (parent.subtypes || []).forEach(subtype => identityNames.set(`${parent.id}/${subtype.id}`, subtype.display_name));
  });
  currentContext = { meta, range, decks, completeness, identityNames };
  const hs = completeness.high_score_decklist_completeness;
  const expandable = range.archetypes.filter(item => activeStatisticsSubtypes(item).length >= 2);
  const sortHeader = (label, key, tip) => {
    const arrow = state.statsSort === key ? (state.statsDirection === "desc" ? " ▼" : " ▲") : "";
    return `<button class="sort-button" type="button" data-stats-sort="${key}">${label}${arrow}</button>${tip ? infoTip(tip) : ""}`;
  };
  return `<section class="source-note">
      <p>${t("source.stats")}</p>
      <p>${t("stats.updated", {
        rules: dateText(meta.rules_updated),
        data: dateText(meta.data_updated),
      })}</p>
    </section>
    ${rangeButtons(state.statsRange, "data-stats-range")}
    <div class="period-info">
      <span>${t("stats.period", {
        start: range.period.start,
        end: range.period.end,
        decks: range.total_decks,
        high: range.total_high_score,
        top8: range.total_top8,
      })}</span>
      <strong>${t("stats.completeness", {
        observed: hs.observed_decklist_count,
        expected: hs.expected_decklist_count_display ?? hs.expected_decklist_count,
        rate: pct(hs.completeness_rate),
      })}</strong>
    </div>
    ${chartHtml(archetypes)}
    <section class="panel">
      <div class="panel-toolbar"><h2>${t("stats.title")}</h2>
        ${expandable.length ? `<button id="stats-expand-all" class="secondary-button" type="button">${state.statsExpanded.size ? t("stats.hide_subtypes") : t("stats.show_subtypes")}</button>` : ""}
      </div>
      <p class="real-data-note">${t("stats.note")}</p>
      <div class="table-scroll"><table class="data-table metric-columns" style="width:980px;min-width:100%">
        ${fixedColumns(7)}
        <thead><tr><th>${sortHeader(t("stats.deck"), "name")}</th>
          <th class="number">${sortHeader(t("stats.average_points"), "avg_points_per_round", t("stats.average_points_tip"))}</th>
          <th class="number">${sortHeader(t("stats.high_count"), "high_score_count")}</th>
          <th class="number">${sortHeader(t("stats.high_share"), "high_score_share")}</th>
          <th class="number">${sortHeader(t("stats.top8_count"), "top8_count")}</th>
          <th class="number">${sortHeader(t("stats.top8_share"), "top8_share")}</th>
          <th class="number">${sortHeader(t("stats.conversion"), "conversion", t("stats.conversion_tip"))}</th>
        </tr></thead><tbody>${statsRows(archetypes)}</tbody>
      </table></div>
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
  return `<div class="table-scroll matrix-scroll"><table class="matchup-table">
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
              <span class="axis-toggle">${open ? "−" : "+"}</span><span>${escapeHtml(row.name)}</span></button>`
          : `<span>${escapeHtml(row.name)}</span>`;
        return `<tr><th class="row-head ${row.kind === "subtype" ? "subtype-head" : ""}">${content}</th>
          ${matrixCell(view.overall[row.id])}${view.columns.map(column => matrixCell(view.matrix[row.id][column.id])).join("")}</tr>`;
      }).join("")}
    </tbody></table></div><div id="matrix-record" class="matrix-record" role="status" hidden></div>
    <div id="matrix-hover-pop" class="matrix-hover-pop" role="tooltip" hidden></div>`;
}

async function matchupView() {
  const { document, completeness } = await MtgoController
    .loadMatchup(state.format, state.matchupRange);
  const displayDocument = ReviewData.activeMatchupDocument(document, LOW_SAMPLE_THRESHOLD);
  currentContext = { matchupDocument: displayDocument, completeness };
  const coverage = completeness.matchup_coverage;
  return `${rangeButtons(state.matchupRange, "data-matchup-range")}
    <section class="source-note">
      <p>${t("source.matchups")}</p>
      <p><strong>${t("matchup.completeness", {
        expected: coverage.expected_event_count,
        available: coverage.available_event_count,
        rate: pct(coverage.completeness_rate),
        deferred: coverage.deferred_event_count,
        missing: coverage.missing_event_count,
        excluded: coverage.excluded_event_count,
      })}</strong></p>
    </section>
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
  currentContext = { top8Index: index, top8, bases };
  return `<section class="source-note"><p>${t("source.top8")}</p></section>
    <div class="select-row"><label for="top8-week">${t("top8.week")}</label>
      <select id="top8-week">${index.weeks.map(item => (
        `<option value="${escapeHtml(item.file)}" ${item.file === state.top8WeekFile ? "selected" : ""}>${item.start} ～ ${item.end}</option>`
      )).join("")}</select>
    </div>
    <section class="panel"><p class="real-data-note">${t("top8.summary", {
      events: top8.events.length,
      placements: top8.events.reduce((sum, event) => sum + event.placements.length, 0),
    })}</p>
      <div class="table-scroll"><table class="top8-table top8-week-table"><thead><tr><th>${t("top8.rank")}</th>
        ${top8.events.map(event => `<th title="${escapeHtml(event.name)}"><strong>${escapeHtml(event.display_name)}</strong>
          <small>${event.date} · ${t("top8.players", { count: event.player_count })}</small></th>`).join("")}
      </tr></thead><tbody>${Array.from({ length: 8 }, (_, offset) => {
        const rank = offset + 1;
        return `<tr><td>${rank}</td>${top8.events.map(event => {
          const placement = event.placements.find(item => item.rank === rank);
          if (!placement || placement.deck_status !== "available") return `<td class="missing-deck">${t("top8.unavailable")}</td>`;
          return `<td><button class="name-button" type="button" data-top8-detail="${escapeHtml(event.event_id)}:${rank}">${escapeHtml(placement.identity.display_name)}</button></td>`;
        }).join("")}</tr>`;
      }).join("")}</tbody></table></div>${top8PlacementDetail()}</section>`;
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
  return `<section class="source-note"><p>${t("source.pickup")}</p></section>
    <div class="pickup-layout"><aside class="pickup-weeks"><h2>${t("pickup.archive")}</h2>${index.weeks.map(item => (
      `<button type="button" data-pickup-week="${escapeHtml(item.file)}" class="${item.file === state.pickupWeekFile ? "active" : ""}">
        ${escapeHtml(item.week)}<span>${item.start} ～ ${item.end}</span></button>`
    )).join("")}</aside><div class="pickup-content">${groups.map(([title, key]) => (
      `<section class="pickup-group"><h2>${title}</h2>${document[key]?.length
        ? document[key].map(item => pickupDeck(item, key)).join("")
        : `<p class="pickup-empty">${t("pickup.empty")}</p>`}</section>`
    )).join("")}</div></div>`;
}
