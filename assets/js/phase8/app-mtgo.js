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

function compositionAction(parent) {
  const subtypes = activeStatisticsSubtypes(parent);
  if (subtypes.length === 1) {
    return {
      kind: "detail",
      identity: `${parent.id}/${subtypes[0].id}`,
    };
  }
  if (subtypes.length >= 2) {
    return {
      kind: "subtypes",
      parentId: parent.id,
    };
  }
  return { kind: "detail", identity: parent.id };
}

function currentCompositionAction(parentId) {
  if (state.product === "mtgo-landing") {
    return { kind: "detail", identity: parentId };
  }
  const parent = currentContext?.range?.archetypes
    ?.find(item => item.id === parentId);
  return parent ? compositionAction(parent) : { kind: "detail", identity: parentId };
}

function landingTargetUrl(parameters) {
  const target = new URL(window.location.href);
  target.search = "";
  Object.entries(parameters).forEach(([key, value]) => target.searchParams.set(key, value));
  target.searchParams.set("lang", I18n.language());
  return `${target.pathname}${target.search}`;
}

function landingDeckUrl(deck, weekId) {
  return landingTargetUrl({
    format: state.format,
    product: "mtgo-top8",
    week: weekId,
    detail: `${deck.event_id}:${deck.final_rank}`,
  });
}

function landingSummaryText(item, weekId) {
  const text = localizedValue(item.text);
  const links = new Map((item.deck_links || []).map(link => [link.token, link]));
  const tokens = [...links.keys()].sort((left, right) => right.length - left.length);
  if (!tokens.length) return escapeHtml(text);
  const pattern = new RegExp(`(${tokens.map(token => (
    token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  )).join("|")})`, "g");
  return text.split(pattern).map(part => {
    const link = links.get(part);
    if (!link) return escapeHtml(part);
    return `<a class="landing-deck-link" href="${escapeHtml(landingDeckUrl(link.deck, weekId))}">${escapeHtml(localizedValue(link.label))}</a>`;
  }).join("");
}

function landingSummaryHtml(landing) {
  const items = [...(landing.weekly_summary?.items || [])]
    .sort((left, right) => Number(left.order) - Number(right.order));
  if (!items.length) {
    return `<p class="landing-empty">${t("landing.summary_empty")}</p>`;
  }
  return `<div class="landing-brief-lines">${items.map(item => (
    `<article class="landing-brief-line"><span class="landing-brief-icon" aria-hidden="true">◇</span><p>${landingSummaryText(item, landing.week.id)}</p></article>`
  )).join("")}</div>`;
}

function landingCompositionHtml(landing) {
  const rows = landing.environment?.rows || [];
  const segments = rows.map((row, index) => {
    const representative = REPRESENTATIVE_CARDS[state.format]?.[row.archetype_id]?.[0];
    return {
      id: row.archetype_id,
      name: row.display_name,
      share: Number(row.current?.share) || 0,
      color: `composition-color-${index % 6 + 1}`,
      image: representative?.image,
    };
  });
  const other = landing.environment?.other_classified?.current?.share;
  const unknown = landing.environment?.unknown?.current?.share;
  if (Number(other) > 0) {
    segments.push({ name: t("chart.other"), share: Number(other), color: "other" });
  }
  if (Number(unknown) > 0) {
    segments.push({ name: t("chart.unknown"), share: Number(unknown), color: "unknown" });
  }
  const assigned = segments.reduce((sum, segment) => sum + segment.share, 0);
  if (assigned < 0.99999) {
    segments.push({
      name: t("chart.unassigned"),
      share: Math.max(0, 1 - assigned),
      color: "unassigned",
    });
  }
  return `<div class="landing-composition-wrap"><div class="composition-bar landing-composition-bar" role="group" aria-label="${t("landing.composition_aria")}">${segments.map(segment => {
    const label = `${segment.name} · ${pct(segment.share)}`;
    const selected = segment.id === state.compositionIdentity;
    return accessibleCompositionSegment({
      className: `composition-segment ${segment.color}${segment.image ? " has-card-art" : ""}${selected ? " selected" : ""}`,
      style: `--composition-share:${(segment.share * 100).toFixed(6)}%${segment.image ? `;--composition-image:url(${segment.image})` : ""}`,
      label,
      identity: segment.id,
      expanded: selected,
    });
  }).join("")}</div><p class="composition-note">${t("landing.composition_note")}</p></div>`;
}

function landingDirection(row, comparisonAvailable) {
  if (!comparisonAvailable || row.previous_four_weeks?.share === null) {
    return { className: "unavailable", symbol: "—", label: t("landing.direction_unavailable") };
  }
  const delta = Number(row.current?.share) - Number(row.previous_four_weeks?.share);
  if (delta >= 0.05) return { className: "up", symbol: "↑", label: t("landing.direction_up") };
  if (delta <= -0.05) return { className: "down", symbol: "↓", label: t("landing.direction_down") };
  return { className: "steady", symbol: "—", label: t("landing.direction_steady") };
}

function representativeImagePath(path) {
  return path?.replace(/^\.\.\/images\//, "assets/images/") || "";
}

function landingRepresentatives(row) {
  const configured = REPRESENTATIVE_CARDS[state.format]?.[row.archetype_id] || [];
  const cards = (row.key_cards || []).map(card => (
    configured.find(candidate => candidate.name === card.name) || card
  ));
  if (!cards.length) return `<span class="landing-cards-empty">${t("landing.cards_unavailable")}</span>`;
  return `<div class="landing-representatives" aria-label="${t("landing.representative_cards")}">${cards.map(card => {
    const search = `https://scryfall.com/search?q=${encodeURIComponent(`!"${card.name}"`)}`;
    const image = `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(card.name)}&format=image&version=normal`;
    const source = representativeImagePath(card.image);
    return source
      ? `<a class="landing-representative card-link" href="${escapeHtml(search)}" target="_blank" rel="noopener" data-card-image="${escapeHtml(image)}" data-card-name="${escapeHtml(card.name)}" data-scryfall-url="${escapeHtml(search)}"><span class="card-image-frame is-loading"><img alt="${escapeHtml(card.name)}" data-progressive-image="${escapeHtml(source)}" data-image-owner="landing-representative"><span class="card-image-placeholder">${escapeHtml(card.name)}</span></span></a>`
      : `<span class="landing-representative landing-card-placeholder">${escapeHtml(card.name)}</span>`;
  }).join("")}</div>`;
}

function landingEnvironmentDetail(row) {
  if (state.detailIdentity !== row.archetype_id || !currentContext.environmentDecks) return "";
  const deck = locateDeck(currentContext.environmentDecks, row.archetype_id);
  if (!deck) return "";
  return deckDetailHtml({
    title: row.display_name,
    bestDeck: deck.best_deck,
    averageDeck: deck.average_deck,
    comparison: { rank: deck.best_deck?.final_rank },
    closeAction: "data-close-detail",
    className: "deck-detail landing-inline-detail",
    responsiveKey: `landing:${row.archetype_id}`,
  });
}

function landingEnvironmentRows(landing) {
  return (landing.environment?.rows || []).map(row => {
    const direction = landingDirection(row, landing.comparison?.available);
    const open = state.detailIdentity === row.archetype_id;
    return `<tbody class="landing-environment-group"><tr class="landing-environment-row" data-landing-row="${escapeHtml(row.archetype_id)}">
      <td class="landing-deck-cell"><button class="landing-deck-button" type="button" data-detail-identity="${escapeHtml(row.archetype_id)}" aria-expanded="${open}">${manaIdentityHtml(row.archetype_id)}<span>${escapeHtml(row.display_name)}</span></button></td>
      <td class="landing-cards-cell">${landingRepresentatives(row)}</td>
      <td class="landing-share-cell" data-label="${t("landing.current_short")}">${pct(row.current?.share)}</td>
      <td class="landing-share-cell" data-label="${t("landing.previous_short")}">${pct(row.previous_week?.share)}</td>
      <td class="landing-share-cell" data-label="${t("landing.four_weeks_short")}">${pct(row.previous_four_weeks?.share)}</td>
      <td class="landing-trend-cell" data-label="${t("landing.trend")}"><span class="landing-trend ${direction.className}" title="${escapeHtml(direction.label)}" aria-label="${escapeHtml(direction.label)}">${direction.symbol}</span></td>
    </tr>${open ? `<tr class="landing-detail-row" data-landing-detail="${escapeHtml(row.archetype_id)}"><td colspan="6">${landingEnvironmentDetail(row)}</td></tr>` : ""}</tbody>`;
  }).join("");
}

function landingEnvironmentHtml(landing) {
  const statisticsUrl = landingTargetUrl({
    format: state.format,
    product: "mtgo-statistics",
    range: "1",
  });
  return `<section class="panel landing-environment" id="environment"><div class="landing-panel-head"><div><h2>${t("landing.environment_title")}</h2><p>${t("landing.environment_subtitle")}</p></div><p class="landing-interaction-note"><span class="desktop-instruction">${t("chart.desktop_instruction")}</span><span class="mobile-instruction">${t("chart.mobile_instruction")}</span></p></div>
    ${landingCompositionHtml(landing)}
    <div class="landing-environment-table-wrap"><table class="landing-environment-table"><thead><tr><th>${t("stats.deck")}</th><th>${t("landing.representative_cards")}</th><th>${t("landing.current")}</th><th>${t("landing.previous")}</th><th>${t("landing.four_weeks")}</th><th>${t("landing.trend")}</th></tr></thead>${landingEnvironmentRows(landing)}</table></div>
    <div class="landing-full-statistics"><a href="${escapeHtml(statisticsUrl)}">${t("landing.full_statistics")} →</a></div></section>`;
}

function landingFeatureItems(context) {
  const currentFile = `${context.landing.week.id}.json`;
  if (context.featureFile === currentFile) return context.landing.features?.items || [];
  return context.pickupDocument?.features?.items || [];
}

function landingFeatureCard(card, index) {
  const name = card.name;
  const search = `https://scryfall.com/search?q=${encodeURIComponent(`!"${name}"`)}`;
  const image = `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=image&version=normal`;
  return `<a class="landing-feature-card card-link" href="${escapeHtml(search)}" target="_blank" rel="noopener" data-card-image="${escapeHtml(image)}" data-card-name="${escapeHtml(name)}" data-scryfall-url="${escapeHtml(search)}"><span class="card-image-frame is-loading"><img alt="${escapeHtml(name)}" data-progressive-image="${escapeHtml(image)}" data-image-owner="landing-feature-${index}"><span class="card-image-placeholder">${escapeHtml(name)}</span></span></a>`;
}

function landingFeatureDetail(item) {
  const identity = item.subtype_id
    ? `${item.archetype_id}/${item.subtype_id}`
    : item.archetype_id;
  const reference = currentContext.featureDecks
    ? locateDeck(currentContext.featureDecks, identity)
    : null;
  return deckDetailHtml({
    title: item.display_name,
    exactDeck: item.deck,
    averageDeck: reference?.average_deck,
    comparison: { rank: item.deck.final_rank },
    closeAction: `data-pickup-toggle="${escapeHtml(`landing:${item.category}:${item.order}`)}"`,
    showDeviation: false,
    className: "deck-detail landing-feature-detail",
    responsiveKey: `landing-feature:${item.category}:${item.order}`,
  });
}

function landingFeatureHtml(item) {
  const id = `landing:${item.category}:${item.order}`;
  const open = state.pickupOpen.has(id);
  const category = item.category === "new_deck"
    ? t("landing.feature_new_deck")
    : t("landing.feature_new_technology");
  return `<article class="landing-feature-item ${open ? "open" : ""}"><div class="landing-feature-summary"><button type="button" class="landing-feature-toggle" data-pickup-toggle="${escapeHtml(id)}" aria-expanded="${open}"><span class="landing-feature-copy"><span class="landing-feature-category">${category}</span><strong>${escapeHtml(localizedValue(item.headline) || item.display_name)}</strong><span>${escapeHtml(localizedValue(item.positioning))}</span></span><span class="landing-feature-sign" aria-hidden="true">${open ? "−" : "+"}</span></button><span class="landing-feature-cards" aria-label="${t("landing.four_cards")}">${item.featured_cards.map(landingFeatureCard).join("")}</span></div>${open ? landingFeatureDetail(item) : ""}</article>`;
}

function landingFeaturesHtml(context) {
  const items = [...landingFeatureItems(context)].sort((left, right) => {
    const category = { new_deck: 0, new_technology: 1 };
    return category[left.category] - category[right.category]
      || Number(left.order) - Number(right.order);
  });
  const groups = ["new_deck", "new_technology"].map(category => {
    const categoryItems = items.filter(item => item.category === category);
    if (!categoryItems.length) return "";
    const label = category === "new_deck"
      ? t("landing.feature_new_deck")
      : t("landing.feature_new_technology");
    return `<div class="landing-feature-group"><h3>${label}</h3>${categoryItems.map(landingFeatureHtml).join("")}</div>`;
  }).join("");
  return `<section class="panel landing-features" id="features"><div class="landing-panel-head"><div><h2>${t("landing.features_title")}</h2><p>${t("landing.features_subtitle")}</p></div></div><div class="landing-feature-week"><label for="landing-feature-week">${t("landing.feature_week")}</label><select id="landing-feature-week">${context.pickupIndex.weeks.map(entry => (
    `<option value="${escapeHtml(entry.file)}" ${entry.file === context.featureFile ? "selected" : ""}>${entry.start} ～ ${entry.end}${entry.file === `${context.landing.week.id}.json` ? `（${t("landing.feature_current")}）` : ""}</option>`
  )).join("")}</select><span>${t("landing.feature_week_note")}</span></div><div class="landing-feature-content">${groups || `<p class="landing-empty">${t("landing.feature_empty")}</p>`}</div></section>`;
}

async function landingView() {
  const context = await MtgoController.loadLanding(
    state.format,
    productEntry().path,
    state.pickupWeekFile,
    {
      includeEnvironmentDecks: Boolean(state.detailIdentity),
      includeFeatureDecks: Boolean(state.pickupOpen.size),
    }
  );
  state.pickupWeekFile = context.featureFile;
  const validEnvironmentIds = new Set((context.landing.environment?.rows || []).map(row => row.archetype_id));
  if (state.detailIdentity && !validEnvironmentIds.has(state.detailIdentity)) {
    state.detailIdentity = null;
    setCompositionSelection(null);
  }
  const featureIds = new Set(landingFeatureItems(context).map(item => (
    `landing:${item.category}:${item.order}`
  )));
  [...state.pickupOpen].forEach(id => {
    if (id.startsWith("landing:") && !featureIds.has(id)) state.pickupOpen.delete(id);
  });
  currentContext = {
    ...context,
    environmentDecks: context.environmentDecks,
    featureDecks: context.featureDecks,
  };
  if (context.landing.state === "no_events") {
    return `<section class="panel landing-no-events"><h2>${t("landing.summary_title")}</h2><p>${t("landing.no_events")}</p></section>`;
  }
  return `<section class="panel landing-brief" id="weekly-brief"><div class="landing-panel-head"><div><h2>${t("landing.summary_title")}</h2><p>${context.landing.week.start} ～ ${context.landing.week.end} · ${formatLabel(state.format)}</p></div></div>${landingSummaryHtml(context.landing)}</section>
    ${landingFreshness(context.landing, context.range, context.completeness)}
    ${landingEnvironmentHtml(context.landing)}
    ${landingFeaturesHtml(context)}`;
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
      subtypes.forEach((subtype, index) => {
        const identityId = `${parent.id}/${subtype.id}`;
        rows.push(statsRow(
          subtype,
          `<button class="name-button" type="button" data-detail-identity="${escapeHtml(identityId)}"
            data-responsive-key="stats-action:${escapeHtml(identityId)}" aria-expanded="${state.detailIdentity === identityId}">
            ${manaIdentityHtml(identityId)}<span class="identity-label">${escapeHtml(subtype.display_name)}</span></button>`,
          "subtype-row",
          index === subtypes.length - 1
            ? ` data-stats-subtype-end="${escapeHtml(parent.id)}"`
            : ""
        ));
        if (state.detailIdentity === identityId) rows.push(statsDetailRow(identityId));
      });
    }
    return rows.join("");
  }).join("");
}

function statsRow(record, nameHtml, rowClass, rowAttributes = "") {
  return `<tr class="${rowClass}"${rowAttributes}>
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
    action: compositionAction(item),
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
    const expanded = item.id === state.compositionIdentity;
    const className = `composition-segment ${item.color}${item.image ? " has-card-art" : ""}${expanded ? " selected" : ""}`;
    const style = `--composition-share:${(item.share * 100).toFixed(6)}%${item.image ? `;--composition-image:url(${item.image})` : ""}`;
    return accessibleCompositionSegment({
      className,
      style,
      label: detail,
      identity: item.id,
      expanded,
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

function matchupFilterCandidates(document) {
  return ReviewData.filterCandidates(document);
}

function matchupFilterCandidateIds(document) {
  return matchupFilterCandidates(document).flatMap(parent => [
    parent.id,
    ...parent.children.map(child => child.id),
  ]);
}

function synchronizeMatchupFilter(document) {
  if (state.matchupFilterIdentities === null) return;
  const available = new Set(matchupFilterCandidateIds(document));
  state.matchupFilterIdentities = new Set(
    [...state.matchupFilterIdentities].filter(identity => available.has(identity))
  );
  if (!state.matchupFilterIdentities.size) {
    state.matchupFilterIdentities = null;
    state.matchupRows.clear();
  }
}

function matchupFilterControls(document) {
  const candidates = matchupFilterCandidates(document);
  const allIds = matchupFilterCandidateIds(document);
  const committed = state.matchupFilterIdentities;
  const selection = state.matchupFilterOpen
    ? state.matchupFilterDraft
    : committed === null ? new Set(allIds) : committed;
  const allSelected = selection.size === allIds.length;
  const summary = committed === null
    ? t("matchup.filter_all")
    : t("matchup.filter_selected", { count: committed.size });
  const groups = candidates.map(parent => {
    const childrenId = `matchup-filter-children-${parent.id}`;
    const expanded = state.matchupFilterExpanded.has(parent.id);
    const disclosure = parent.children.length
      ? `<button type="button" class="matchup-filter-disclosure" data-matchup-filter-parent="${escapeHtml(parent.id)}"
          aria-expanded="${expanded}" aria-controls="${escapeHtml(childrenId)}" aria-label="${escapeHtml(`${expanded ? t("matchup.collapse") : t("matchup.expand")}${parent.name}`)}">
          <span aria-hidden="true">${expanded ? "−" : "+"}</span></button>`
      : `<span class="matchup-filter-disclosure-spacer" aria-hidden="true"></span>`;
    const children = parent.children.map(child => `<label class="matchup-filter-option matchup-filter-child"
        data-matchup-filter-name="${escapeHtml(ReviewData.normalizeSearch(child.name))}">
        <input type="checkbox" data-matchup-filter-option="${escapeHtml(child.id)}"${selection.has(child.id) ? " checked" : ""}>
        <span>${escapeHtml(child.name)}</span></label>`).join("");
    return `<div class="matchup-filter-parent-group" data-matchup-filter-group
        data-matchup-filter-parent-name="${escapeHtml(ReviewData.normalizeSearch(parent.name))}">
      <div class="matchup-filter-parent-row">${disclosure}<label class="matchup-filter-option">
        <input type="checkbox" data-matchup-filter-option="${escapeHtml(parent.id)}"${selection.has(parent.id) ? " checked" : ""}>
        <span>${escapeHtml(parent.name)}</span></label></div>
      ${parent.children.length ? `<div id="${escapeHtml(childrenId)}" class="matchup-filter-children"${expanded ? "" : " hidden"}>${children}</div>` : ""}
    </div>`;
  }).join("");
  return `<div id="matchup-filter-control" class="matchup-filter-control">
    <label id="matchup-filter-label">${t("matchup.filter_label")}</label>
    <div class="matchup-filter-trigger-row">
      <button type="button" class="matchup-filter-toggle" data-matchup-filter-toggle
        aria-expanded="${state.matchupFilterOpen}" aria-controls="matchup-filter-menu">
        <span>${escapeHtml(summary)}</span><span aria-hidden="true">▾</span></button>
      <button type="button" class="secondary-button" data-matchup-filter-reset${committed === null ? " disabled" : ""}>${t("matchup.filter_reset")}</button>
    </div>
    <div id="matchup-filter-menu" class="matchup-filter-menu" data-matchup-filter-menu${state.matchupFilterOpen ? "" : " hidden"}
      role="dialog" aria-labelledby="matchup-filter-label">
      <input id="matchup-filter-search" type="search" placeholder="${t("matchup.filter_search_placeholder")}"
        autocomplete="off" spellcheck="false">
      <label class="matchup-filter-select-all"><input type="checkbox" data-matchup-filter-select-all${allSelected ? " checked" : ""}>
        <span>${t("matchup.filter_select_all")}</span></label>
      <div class="matchup-filter-tree">${groups}</div>
      <p class="matchup-filter-count" data-matchup-filter-count>${t("matchup.filter_count", { count: selection.size })}</p>
      <div class="matchup-filter-actions">
        <button type="button" class="primary-button" data-matchup-filter-apply${selection.size ? "" : " disabled"}>${t("matchup.filter_apply")}</button>
        <button type="button" class="secondary-button" data-matchup-filter-cancel>${t("matchup.filter_cancel")}</button>
      </div>
    </div>
  </div>`;
}

function matchupMainstreamControl(source, unavailable = false) {
  const helpKey = source === "mtgo"
    ? "matchup.mainstream_mtgo_help"
    : "matchup.mainstream_tabletop_help";
  const status = state.matchupMainstreamOnly && unavailable
    ? `<div class="matchup-mainstream-status" role="status">
        <span>${t("matchup.mainstream_unavailable")}</span>
        <button type="button" class="secondary-button" data-matchup-mainstream-retry>${t("matchup.mainstream_retry")}</button>
      </div>`
    : "";
  return `<div class="matchup-mainstream-control">
    <label><input type="checkbox" data-matchup-mainstream${state.matchupMainstreamOnly ? " checked" : ""}>
      <span>${t("matchup.mainstream_label")}</span>${infoTip(t(helpKey))}</label>
    ${status}
  </div>`;
}

function matchupViewControls(document, source, unavailable = false) {
  return `<div class="matchup-view-controls">
    ${matchupFilterControls(document)}
    ${matchupMainstreamControl(source, unavailable)}
  </div>`;
}

function prepareMatchupFilterDraft(document) {
  const allIds = matchupFilterCandidateIds(document);
  state.matchupFilterDraft = state.matchupFilterIdentities === null
    ? new Set(allIds)
    : new Set(state.matchupFilterIdentities);
}

function updateMatchupFilterCandidateVisibility(searchQuery) {
  const query = ReviewData.normalizeSearch(searchQuery);
  document.querySelectorAll("[data-matchup-filter-group]").forEach(group => {
    const parentMatch = group.dataset.matchupFilterParentName.includes(query);
    const children = [...group.querySelectorAll("[data-matchup-filter-name]")];
    const matchingChildren = children.filter(child => child.dataset.matchupFilterName.includes(query));
    group.hidden = Boolean(query && !parentMatch && !matchingChildren.length);
    children.forEach(child => child.hidden = Boolean(query && !child.dataset.matchupFilterName.includes(query)));
    const childList = group.querySelector(".matchup-filter-children");
    if (!childList) return;
    const parentId = group.querySelector("[data-matchup-filter-parent]")?.dataset.matchupFilterParent;
    childList.hidden = query
      ? !matchingChildren.length
      : !state.matchupFilterExpanded.has(parentId);
  });
}

function updateMatchupFilterDraftControls(document) {
  const allIds = matchupFilterCandidateIds(document);
  globalThis.document.querySelectorAll("[data-matchup-filter-option]").forEach(option => {
    option.checked = state.matchupFilterDraft.has(option.dataset.matchupFilterOption);
  });
  const selectAll = globalThis.document.querySelector("[data-matchup-filter-select-all]");
  if (selectAll) {
    selectAll.checked = state.matchupFilterDraft.size === allIds.length;
    selectAll.indeterminate = state.matchupFilterDraft.size > 0
      && state.matchupFilterDraft.size < allIds.length;
  }
  const count = globalThis.document.querySelector("[data-matchup-filter-count]");
  if (count) count.textContent = t("matchup.filter_count", { count: state.matchupFilterDraft.size });
  const apply = globalThis.document.querySelector("[data-matchup-filter-apply]");
  if (apply) apply.disabled = !state.matchupFilterDraft.size;
}

function setMatchupFilterMenuOpen(open, document) {
  state.matchupFilterOpen = open;
  const toggle = globalThis.document.querySelector("[data-matchup-filter-toggle]");
  const menu = globalThis.document.querySelector("[data-matchup-filter-menu]");
  if (!toggle || !menu) return;
  toggle.setAttribute("aria-expanded", String(open));
  menu.hidden = !open;
  if (!open) {
    toggle.focus({ preventScroll: true });
    return;
  }
  prepareMatchupFilterDraft(document);
  const search = globalThis.document.querySelector("#matchup-filter-search");
  if (search) search.value = "";
  updateMatchupFilterCandidateVisibility("");
  updateMatchupFilterDraftControls(document);
  positionMatchupFilterMenu();
  search?.focus({ preventScroll: true });
}

function positionMatchupFilterMenu() {
  const control = document.querySelector("#matchup-filter-control");
  const menu = document.querySelector("[data-matchup-filter-menu]:not([hidden])");
  if (!control || !menu) return;
  const margin = 12;
  const gap = 6;
  const rect = control.getBoundingClientRect();
  const availableBelow = window.innerHeight - rect.bottom - gap - margin;
  const availableAbove = rect.top - gap - margin;
  const openAbove = availableBelow < 280 && availableAbove > availableBelow;
  const availableHeight = Math.min(
    window.innerHeight - (margin * 2),
    Math.max(180, openAbove ? availableAbove : availableBelow)
  );
  const width = Math.min(rect.width, window.innerWidth - (margin * 2));
  const left = Math.max(margin, Math.min(rect.left, window.innerWidth - width - margin));
  menu.style.position = "fixed";
  menu.style.left = `${left}px`;
  menu.style.width = `${width}px`;
  menu.style.maxHeight = `${availableHeight}px`;
  if (openAbove) {
    menu.style.top = "auto";
    menu.style.bottom = `${window.innerHeight - rect.top + gap}px`;
  } else {
    menu.style.top = `${rect.bottom + gap}px`;
    menu.style.bottom = "auto";
  }
}

function matchupDetailIdentity(document, row) {
  if (row.kind === "subtype") return row.id;
  const parent = document.hierarchy.parents.find(item => item.id === row.parentId);
  return parent?.subtype_ids?.length === 1 ? parent.subtype_ids[0] : row.id;
}

function matchupDetailUrl(identityId) {
  const tabletop = state.product === "tabletop-major-events";
  const entryKey = tabletop ? "tabletopEntry" : "mtgoEntry";
  const entry = globalThis.document.documentElement.dataset[entryKey];
  if (!entry) throw new Error(`Missing ${tabletop ? "tabletop" : "mtgo"} entry path`);
  const target = new URL(entry, window.location.href);
  target.search = "";
  target.searchParams.set("format", state.format);
  target.searchParams.set("product", tabletop ? "tabletop-major-events" : "mtgo-statistics");
  if (tabletop) {
    target.searchParams.set("view", "overview");
    if (state.tabletopEventId) target.searchParams.set("event", state.tabletopEventId);
    target.searchParams.set("scope", state.tabletopScope);
    target.searchParams.set("sort", state.tabletopSort);
    target.searchParams.set("dir", state.tabletopDirection);
  } else {
    target.searchParams.set("range", String(state.matchupRange));
    target.searchParams.set("sort", state.statsSort);
    target.searchParams.set("dir", state.statsDirection);
  }
  target.searchParams.set("detail", identityId);
  target.searchParams.set("lang", I18n.language());
  return target.href;
}

function matrixHtml(document) {
  const mainstreamParentIds = state.matchupMainstreamOnly
    && !currentContext.matchupMainstreamUnavailable
    ? currentContext.matchupMainstreamParentIds
    : null;
  const view = ReviewData.buildVisibleView(
    document,
    state.matchupRows,
    state.matchupColumns,
    state.matchupFilterIdentities,
    mainstreamParentIds
  );
  if (!view.rows.length) {
    return `<div class="empty-state matchup-filter-empty" role="status">
      <p>${t(mainstreamParentIds === null ? "matchup.filter_empty" : "matchup.mainstream_filter_empty")}</p>
      <button class="secondary-button" type="button" data-matchup-filter-reset>${t("matchup.filter_reset")}</button>
    </div>`;
  }
  const table = `<table class="matchup-table">
    <thead><tr><th class="corner"></th><th class="column-head overall">${t("matchup.overall")}</th>
      ${view.columns.map(column => {
        const open = state.matchupColumns.has(column.parentId);
        const content = column.kind === "archetype" && column.expandable
          ? `<button type="button" class="axis-disclosure-button column-axis-controls" data-matchup-column="${escapeHtml(column.parentId)}"
              aria-label="${escapeHtml(`${open ? t("matchup.collapse") : t("matchup.expand")}${column.name}`)}">
              <span class="column-axis-toggle" aria-hidden="true">${open ? "−" : "+"}</span>
              <span class="axis-name">${escapeHtml(column.name)}</span></button>`
          : `<div class="column-axis-controls"><span class="axis-name">${escapeHtml(column.name)}</span></div>`;
        return `<th class="column-head ${column.kind === "subtype" ? "subtype-head" : ""}">
          ${content}</th>`;
      }).join("")}
    </tr></thead><tbody>
      ${view.rows.map(row => {
        const open = state.matchupRows.has(row.parentId);
        const content = row.kind === "archetype" && row.expandable
          ? `<button type="button" class="axis-disclosure-button row-axis-controls" data-matchup-row="${escapeHtml(row.parentId)}"
              aria-label="${escapeHtml(`${open ? t("matchup.collapse") : t("matchup.expand")}${row.name}`)}">
              <span class="row-axis-toggle" aria-hidden="true">${open ? "−" : "+"}</span>
              <span class="row-axis-name" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</span></button>`
          : `<div class="row-axis-controls"><a class="row-axis-detail-link"
              href="${escapeHtml(matchupDetailUrl(matchupDetailIdentity(document, row)))}" target="_blank" rel="noopener"
              aria-label="${escapeHtml(t("matchup.open_detail", { name: row.name }))}">
              <span class="row-axis-detail-content"><span class="row-axis-name" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</span>
              <svg class="axis-detail-external" viewBox="0 0 16 16" aria-hidden="true"><path d="M9 2h5v5M14 2 8 8M12 9v4a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h4" /></svg></span></a></div>`;
        return `<tr data-matchup-row-identity="${escapeHtml(row.id)}">
          <th class="row-head ${row.kind === "subtype" ? "subtype-head" : ""}">
            ${content}</th>
          ${matrixCell(view.overall[row.id])}${view.columns.map(column => matrixCell(view.matrix[row.id][column.id])).join("")}</tr>`;
      }).join("")}
    </tbody></table>`;
  return `${horizontalScrollFrame("matchup", "table-scroll matrix-scroll", table, matrixStickyHeader(view.columns))}<div id="matrix-record" class="matrix-record" role="status" hidden></div>
    <div id="matrix-hover-pop" class="matrix-hover-pop" role="tooltip" hidden></div>`;
}

function matchupProjection(document) {
  return `<div id="matchup-projection">${matrixHtml(document)}</div>`;
}

async function mtgoMainstreamProjection() {
  if (!state.matchupMainstreamOnly) {
    return { parentIds: null, unavailable: false };
  }
  try {
    const range = await MtgoController.loadRangeStatistics(
      state.format,
      state.matchupRange
    );
    const parentIds = ReviewData.mainstreamParentIds(
      range.archetypes,
      "id",
      "high_score_share"
    );
    return parentIds === null
      ? { parentIds: null, unavailable: true }
      : { parentIds, unavailable: false };
  } catch {
    return { parentIds: null, unavailable: true };
  }
}

async function matchupView() {
  const [{ document, completeness }, mainstream] = await Promise.all([
    MtgoController.loadMatchup(state.format, state.matchupRange),
    mtgoMainstreamProjection(),
  ]);
  const displayDocument = ReviewData.activeMatchupDocument(document, LOW_SAMPLE_THRESHOLD);
  currentContext = {
    matchupDocument: displayDocument,
    completeness,
    matchupMainstreamParentIds: mainstream.parentIds,
    matchupMainstreamUnavailable: mainstream.unavailable,
  };
  synchronizeMatchupFilter(displayDocument);
  return `${rangeButtons(state.matchupRange, "data-matchup-range")}
    <aside class="source-note" aria-label="${t("source.label")}">
      <p>${t("source.matchups")}</p>
    </aside>
    ${matchupFreshness(completeness)}
    <section class="panel"><div class="panel-toolbar"><div><h2>${t("matchup.title")}</h2>
      <p class="matrix-toolbar-note">${t("matchup.note")}</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? t("matchup.collapse_all") : t("matchup.expand_all")}</button>
    </div>${matchupViewControls(displayDocument, "mtgo", mainstream.unavailable)}${matchupLegend(displayDocument.min_sample_hint)}${matchupProjection(displayDocument)}</section>`;
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
  const deviation = item.deviation === null || item.deviation === undefined
    ? "—"
    : t("deck.points", { count: item.deviation });
  return `<article class="pickup-card ${open ? "open" : ""}">
    <button type="button" class="pickup-head" data-pickup-toggle="${escapeHtml(id)}" aria-expanded="${open}">
      <span><strong>${escapeHtml(item.archetype)}</strong><small>${escapeHtml(item.player)} · ${t("deck.rank")} ${item.final_rank}
      · ${t("deck.points", { count: item.swiss_score })} · ${dateText(item.starttime)}</small></span><b>${title} · ${t("deck.deviation")} ${deviation}</b>
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
