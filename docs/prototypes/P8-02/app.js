const state = {
  format: "modern",
  product: "stats",
  statsRange: 1,
  statsSortKey: "hsShare",
  statsSortDirection: "desc",
  matchupRange: 4,
  expandedStats: new Set(),
  matchupRows: new Set(),
  matchupColumns: new Set(),
  deckDetail: null,
  deckMode: "average",
  top8Week: "2026-07-13",
  tabletopScope: "all_constructed",
  tabletopView: "overview",
  tabletopEvent: "434455",
  tabletopSelectedEvents: new Set(["434455"]),
  tabletopExpanded: new Set(),
  pickupWeek: "2026-W27",
  pickupOpen: new Set(),
};

const formats = {
  standard: { label: "标准", products: ["stats", "matchup", "top8", "pickup"] },
  modern: { label: "摩登", products: ["stats", "matchup", "top8", "tabletop"] },
  pauper: { label: "纯铁", products: [] },
  pioneer: { label: "先驱", products: [] },
  legacy: { label: "薪传", products: [] },
  vintage: { label: "特选", products: [] },
};

const products = [
  { id: "stats", label: "MTGO官方数据统计" },
  { id: "matchup", label: "MTGO对阵胜率" },
  { id: "top8", label: "MTGO八强牌表" },
  { id: "tabletop", label: "实体大赛" },
  { id: "pickup", label: "每周精选套牌" },
];

const modernArchetypes = [
  {
    id: "broodscale",
    name: "Broodscale Combo",
    avg: 1.82,
    hs: 27,
    hsShare: 0.278,
    top8: 6,
    top8Share: 0.107,
    conversion: 0.222,
    subtypes: [
      { id: "gruul-broodscale", name: "Gruul Broodscale Combo", avg: 1.91, hs: 10, hsShare: 0.103, top8: 3, top8Share: 0.054, conversion: 0.300 },
      { id: "mono-green-broodscale", name: "Mono-Green Broodscale Combo", avg: 1.79, hs: 17, hsShare: 0.175, top8: 3, top8Share: 0.054, conversion: 0.176 },
      { id: "golgari-broodscale", name: "Golgari Broodscale Combo", avg: null, hs: 0, hsShare: 0, top8: 0, top8Share: 0, conversion: null },
    ],
  },
  { id: "boros-energy", name: "Boros Energy", avg: 1.73, hs: 18, hsShare: 0.186, top8: 4, top8Share: 0.071, conversion: 0.222, subtypes: [] },
  {
    id: "prowess",
    name: "Prowess",
    avg: 1.69,
    hs: 15,
    hsShare: 0.155,
    top8: 3,
    top8Share: 0.054,
    conversion: 0.200,
    subtypes: [
      { id: "izzet-prowess", name: "Izzet Prowess", avg: 1.75, hs: 8, hsShare: 0.082, top8: 2, top8Share: 0.036, conversion: 0.250 },
      { id: "grixis-prowess", name: "Grixis Prowess", avg: 1.61, hs: 7, hsShare: 0.072, top8: 1, top8Share: 0.018, conversion: 0.143 },
    ],
  },
  { id: "amulet-titan", name: "Amulet Titan", avg: 1.64, hs: 12, hsShare: 0.124, top8: 2, top8Share: 0.036, conversion: 0.167, subtypes: [] },
  { id: "eldrazi-tron", name: "Eldrazi Tron", avg: 1.58, hs: 9, hsShare: 0.093, top8: 1, top8Share: 0.018, conversion: 0.111, subtypes: [{ id: "colorless-eldrazi-tron", name: "Colorless Eldrazi Tron" }] },
];

const standardArchetypes = [
  { id: "selesnya-offense", name: "Selesnya Offense", avg: 1.85, hs: 28, hsShare: 0.2887, top8: 17, top8Share: 0.3036, conversion: 0.6071, subtypes: [] },
  { id: "jeskai-lessons", name: "Jeskai Lessons", avg: 1.69, hs: 19, hsShare: 0.1959, top8: 15, top8Share: 0.2679, conversion: 0.7895, subtypes: [] },
  { id: "izzet-prowess-standard", name: "Izzet Prowess", avg: 1.70, hs: 14, hsShare: 0.1443, top8: 8, top8Share: 0.1429, conversion: 0.5714, subtypes: [] },
  { id: "izzet-spellementals", name: "Izzet Spellementals", avg: 1.53, hs: 13, hsShare: 0.1340, top8: 7, top8Share: 0.1250, conversion: 0.5385, subtypes: [] },
  { id: "four-color-tablet", name: "4-Color Tablet", avg: 1.35, hs: 5, hsShare: 0.0515, top8: 1, top8Share: 0.0179, conversion: 0.2000, subtypes: [] },
  { id: "dimir-excruciator", name: "Dimir Excruciator", avg: 1.39, hs: 4, hsShare: 0.0412, top8: 3, top8Share: 0.0536, conversion: 0.7500, subtypes: [] },
];

function currentArchetypes() {
  return state.format === "standard" ? standardArchetypes : modernArchetypes;
}

const mainCards = [
  ["Ancient Stirrings", 4],
  ["Basking Broodscale", 4],
  ["Blade of the Bloodchief", 3],
  ["Eldrazi Temple", 4],
  ["Kozilek's Command", 4],
  ["Malevolent Rumble", 4],
  ["Urza's Saga", 4],
  ["Walking Ballista", 1],
  ["Writhing Chrysalis", 4],
];
const sideCards = [
  ["Damping Sphere", 2],
  ["Haywire Mite", 2],
  ["Nature's Claim", 2],
  ["Soulless Jailer", 1],
  ["Unholy Heat", 3],
  ["Vexing Bauble", 2],
];
const averageCards = [
  ["Ancient Stirrings", "4.0"],
  ["Basking Broodscale", "4.0"],
  ["Blade of the Bloodchief", "3.3"],
  ["Kozilek's Command", "3.8"],
  ["Malevolent Rumble", "4.0"],
  ["Writhing Chrysalis", "3.9"],
];

const standardMainCards = [
  ["Bleachbone Verge", 3],
  ["Blood Crypt", 4],
  ["Consult the Star Charts", 2],
  ["Deadly Cover-Up", 2],
  ["Duress", 2],
  ["Firebending Lesson", 2],
  ["Flashback", 2],
  ["Great Hall of the Biblioplex", 4],
  ["Inevitable Defeat", 4],
  ["Jeskai Revelation", 4],
];
const standardSideCards = [
  ["Day of Black Sun", 1],
  ["Deadly Cover-Up", 2],
  ["Disdainful Stroke", 1],
  ["Duress", 2],
  ["Flashfreeze", 2],
  ["Mistrise Village", 1],
  ["Nowhere to Run", 1],
  ["Outrageous Robbery", 1],
];
const standardAverageCards = [
  ["Bleachbone Verge", "3.1"],
  ["Consult the Star Charts", "2.4"],
  ["Deadly Cover-Up", "2.2"],
  ["Great Hall of the Biblioplex", "3.7"],
  ["Inevitable Defeat", "3.6"],
  ["Jeskai Revelation", "3.8"],
];

function currentDeckCards() {
  return state.format === "standard"
    ? { main: standardMainCards, side: standardSideCards, average: standardAverageCards }
    : { main: mainCards, side: sideCards, average: averageCards };
}

const modernMatchupParents = [
  { id: "broodscale", name: "Broodscale Combo", subtypes: ["Gruul Broodscale Combo", "Mono-Green Broodscale Combo", "Golgari Broodscale Combo"] },
  { id: "boros-energy", name: "Boros Energy", subtypes: [] },
  { id: "prowess", name: "Prowess", subtypes: ["Izzet Prowess", "Grixis Prowess"] },
  { id: "amulet-titan", name: "Amulet Titan", subtypes: [] },
];

const standardMatchupParents = [
  { id: "four-color-control", name: "4-Color Control", subtypes: ["Inevitable Defeat 4-Color Control", "Rakshasa's Bargain 4-Color Control"] },
  { id: "selesnya-offense", name: "Selesnya Offense", subtypes: [] },
  { id: "izzet-aggro", name: "Izzet Aggro", subtypes: ["Hired Claw Izzet Aggro", "Razorkin Needlehead Izzet Aggro"] },
  { id: "jeskai-lessons", name: "Jeskai Lessons", subtypes: [] },
];

function currentMatchupParents() {
  return state.format === "standard" ? standardMatchupParents : modernMatchupParents;
}

const top8Weeks = [
  { value: "2026-07-13", label: "2026-07-13 ～ 2026-07-19" },
  { value: "2026-07-06", label: "2026-07-06 ～ 2026-07-12" },
  { value: "2026-06-29", label: "2026-06-29 ～ 2026-07-05" },
];
const modernTop8Events = [
  {
    name: "Modern Challenge 32",
    date: "2026-07-19",
    players: 104,
    decks: ["Gruul Broodscale Combo", "Boros Energy", "Izzet Prowess", "Amulet Titan", "Mono-Green Broodscale Combo", "Jeskai Control", "Colorless Eldrazi Tron", "Grixis Prowess"],
  },
  {
    name: "Modern Challenge 64",
    date: "2026-07-18",
    players: 82,
    decks: ["Boros Energy", "Mono-Green Broodscale Combo", "Amulet Titan", "Izzet Prowess", "Dimir Murktide", "Gruul Broodscale Combo", "Jeskai Control", "Domain Zoo"],
  },
  {
    name: "Modern Showcase Challenge",
    date: "2026-07-16",
    players: 126,
    decks: ["Amulet Titan", "Grixis Prowess", "Boros Energy", "Gruul Broodscale Combo", "Jeskai Control", "Mono-Green Broodscale Combo", "Colorless Eldrazi Tron", "Dimir Murktide"],
  },
];

const standardTop8Events = [
  {
    name: "Standard Challenge 32",
    date: "2026-07-19",
    players: 96,
    decks: ["Selesnya Offense", "Jeskai Lessons", "Izzet Prowess", "Izzet Spellementals", "Dimir Excruciator", "4-Color Tablet", "Mono-Green Landfall", "Rakdos Midrange"],
  },
  {
    name: "Standard Challenge 64",
    date: "2026-07-18",
    players: 78,
    decks: ["Jeskai Lessons", "Selesnya Offense", "Izzet Spellementals", "Izzet Prowess", "4-Color Tablet", "Dimir Excruciator", "Mono-Red Aggro", "Simic Ouroboroid"],
  },
  {
    name: "Standard Showcase Challenge",
    date: "2026-07-16",
    players: 118,
    decks: ["Izzet Prowess", "Selesnya Offense", "Jeskai Lessons", "Dimir Excruciator", "Izzet Spellementals", "4-Color Tablet", "Mono-Green Landfall", "Rakdos Midrange"],
  },
];

function currentTop8Events() {
  return state.format === "standard" ? standardTop8Events : modernTop8Events;
}

const tabletopEvents = [
  {
    id: "434455",
    name: "Pro Tour Magic: The Gathering | Marvel Super Heroes",
    date: "2026-07-17 ～ 2026-07-19",
    sortDate: "2026-07-19",
    structure: "mixed",
    structureLabel: "混合赛",
    detail: "摩登＋轮抽 · Melee 赛事 ID 434455",
    sourceUrl: "https://melee.gg/Tournament/View/434455",
    prototype: false,
    scopes: ["day1", "day2", "all_constructed"],
    quality: "362 份牌表中 290 份已分类，72 份保留为 Unknown；1 名被取消资格牌手的数据留档，其涉及的 6 场对局不计入胜率；轮抽和淘汰赛不计入主要摩登统计。",
    summaries: {
      day1: { participants: 362, known: 290, unknown: 72, matches: 861, avg: 1.430, completion: 0.959, high: 168, record: "845-845-42" },
      day2: { participants: 220, known: 181, unknown: 39, matches: 533, avg: 1.470, completion: 0.987, high: 105, record: "526-526-16" },
      all_constructed: { participants: 362, known: 290, unknown: 72, matches: 1394, avg: 1.445, completion: 0.970, high: null, record: "1371-1371-58" },
    },
  },
  {
    id: "prototype-cut",
    name: "原型赛事 A｜区域冠军赛（有 Cut）",
    date: "2026-07-11 ～ 2026-07-12",
    sortDate: "2026-07-12",
    structure: "constructed_day2",
    structureLabel: "纯构筑 · 有 Cut",
    detail: "384 人 · 第一日 9 轮后 Cut 至 64 人 · 第二日 6 轮后八强",
    sourceUrl: null,
    prototype: true,
    scopes: ["day1", "day2", "all_constructed"],
    quality: "原型数据仅用于验证有 Cut 的纯构筑赛事界面，不代表真实赛事或真实统计结果。",
    summaries: {
      day1: { participants: 384, known: 374, unknown: 10, matches: 1648, avg: 1.442, completion: 0.963, high: 132, record: "1618-1618-60" },
      day2: { participants: 64, known: 62, unknown: 2, matches: 184, avg: 1.516, completion: 0.976, high: 29, record: "180-180-8", day2Conversion: 0.167 },
      all_constructed: { participants: 384, known: 374, unknown: 10, matches: 1832, avg: 1.456, completion: 0.965, high: null, record: "1798-1798-68" },
    },
  },
  {
    id: "prototype-single",
    name: "原型赛事 B｜摩登公开赛（无 Cut）",
    date: "2026-07-05",
    sortDate: "2026-07-05",
    structure: "constructed_single_stage",
    structureLabel: "纯构筑 · 无 Cut",
    detail: "226 人 · 全体完成 9 轮瑞士轮后产生八强",
    sourceUrl: null,
    prototype: true,
    scopes: ["all_constructed"],
    quality: "原型数据仅用于验证无 Cut 的单阶段纯构筑赛事界面，不代表真实赛事或真实统计结果。",
    summaries: {
      all_constructed: { participants: 226, known: 221, unknown: 5, matches: 982, avg: 1.468, completion: 0.971, high: 88, record: "963-963-38" },
    },
  },
];

const tabletopRows = [
  { id: "affinity", name: "Affinity", count: 48, share: 0.133, avg: 1.41, winRate: 0.479, completion: 0.971, high: 25, highRate: 0.521, subtypes: [] },
  {
    id: "broodscale",
    name: "Broodscale Combo",
    count: 33,
    share: 0.091,
    avg: 1.67,
    winRate: 0.558,
    completion: 0.982,
    high: 21,
    highRate: 0.636,
    subtypes: [
      { id: "gruul-broodscale", name: "Gruul Broodscale Combo", count: 12, share: 0.033, avg: 1.78, winRate: 0.585, completion: 1, high: 8, highRate: 0.667 },
      { id: "mono-green-broodscale", name: "Mono-Green Broodscale Combo", count: 21, share: 0.058, avg: 1.61, winRate: 0.542, completion: 0.971, high: 13, highRate: 0.619 },
    ],
  },
  { id: "boros-energy", name: "Boros Energy", count: 30, share: 0.083, avg: 1.53, winRate: 0.512, completion: 0.967, high: 17, highRate: 0.567, subtypes: [] },
  {
    id: "prowess",
    name: "Prowess",
    count: 22,
    share: 0.061,
    avg: 1.57,
    winRate: 0.526,
    completion: 0.955,
    high: 13,
    highRate: 0.591,
    subtypes: [
      { id: "izzet-prowess", name: "Izzet Prowess", count: 14, share: 0.039, avg: 1.62, winRate: 0.538, completion: 0.971, high: 9, highRate: 0.643 },
      { id: "grixis-prowess", name: "Grixis Prowess", count: 8, share: 0.022, avg: 1.49, winRate: 0.505, completion: 0.925, high: 4, highRate: 0.500 },
    ],
  },
];

const pickupWeeks = [
  { id: "2026-W27", label: "2026-W27", range: "06-29 ～ 07-05" },
];
const pickupGroups = [
  {
    title: "新科技",
    items: [
      {
        id: "pickup-four-color-tablet",
        name: "4-Color Tablet",
        player: "_Batutinha_",
        rank: 2,
        score: 15,
        date: "2026-07-05",
        deviation: 40,
        comment: "33333",
        main: [["Bleachbone Verge", 3], ["Blood Crypt", 4], ["Consult the Star Charts", 2], ["Deadly Cover-Up", 2], ["Duress", 2], ["Firebending Lesson", 2], ["Flashback", 2], ["Great Hall of the Biblioplex", 4], ["Inevitable Defeat", 4], ["Jeskai Revelation", 4]],
        side: [["Day of Black Sun", 1], ["Deadly Cover-Up", 2], ["Disdainful Stroke", 1], ["Duress", 2], ["Flashfreeze", 2], ["Mistrise Village", 1], ["Nowhere to Run", 1], ["Outrageous Robbery", 1]],
      },
    ],
  },
  {
    title: "新套牌",
    items: [],
  },
];

function pct(value) {
  return value === null || value === undefined ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

function avg(value) {
  return value === null || value === undefined ? "N/A" : Number(value).toFixed(2);
}

function isAvailable(format, product) {
  return formats[format].products.includes(product);
}

function firstAvailableProduct(format) {
  return products.find((product) => isAvailable(format, product.id))?.id || null;
}

function showAvailabilityMessage(text) {
  const node = document.querySelector("#availability-message");
  node.textContent = text;
  node.hidden = !text;
}

function renderNavigation() {
  const formatRoot = document.querySelector("#format-tabs");
  formatRoot.innerHTML = Object.entries(formats).map(([id, format]) => {
    const unavailable = format.products.length === 0;
    return `<button type="button" data-format="${id}" class="${state.format === id ? "active" : ""} ${unavailable ? "unavailable" : ""}" aria-pressed="${state.format === id}" aria-disabled="${unavailable}" title="${unavailable ? "暂未上线，正在开发中" : ""}">${format.label}</button>`;
  }).join("");

  const productRoot = document.querySelector("#product-tabs");
  productRoot.innerHTML = products.map((product) => {
    const available = isAvailable(state.format, product.id);
    return `<button type="button" data-product="${product.id}" class="${state.product === product.id ? "active" : ""} ${available ? "" : "unavailable"}" aria-pressed="${state.product === product.id}" aria-disabled="${!available}" title="${available ? "" : "暂未上线，正在开发中"}">${product.label}</button>`;
  }).join("");

  formatRoot.querySelectorAll("[data-format]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextFormat = button.dataset.format;
      if (!formats[nextFormat].products.length) {
        showAvailabilityMessage(`${formats[nextFormat].label}：暂未上线，正在开发中。`);
        return;
      }
      state.format = nextFormat;
      if (!isAvailable(nextFormat, state.product)) state.product = firstAvailableProduct(nextFormat);
      state.deckDetail = null;
      state.expandedStats.clear();
      state.matchupRows.clear();
      state.matchupColumns.clear();
      showAvailabilityMessage("");
      render();
    });
  });

  productRoot.querySelectorAll("[data-product]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextProduct = button.dataset.product;
      if (!isAvailable(state.format, nextProduct)) {
        showAvailabilityMessage(`${formats[state.format].label}的${products.find((product) => product.id === nextProduct).label}暂未上线，正在开发中。`);
        return;
      }
      state.product = nextProduct;
      state.deckDetail = null;
      showAvailabilityMessage("");
      render();
    });
  });
}

function rangeButtons(selected, dataAttribute) {
  return `<div class="range-buttons" aria-label="统计区间">${[1, 4, 12].map((range) => `<button type="button" class="${selected === range ? "active" : ""}" ${dataAttribute}="${range}">${range} 周</button>`).join("")}</div>`;
}

function infoTip(text) {
  return `<span class="tip" tabindex="0" aria-label="${text}" data-tip="${text}">i</span>`;
}

function fixedDataColumns(columnCount) {
  return `<colgroup><col class="identity-column">${Array.from({ length: columnCount - 1 }, () => '<col class="metric-column">').join("")}</colgroup>`;
}

function hierarchyRows(items, expanded) {
  return items.flatMap((parent) => {
    const expandable = (parent.subtypes || []).length >= 2;
    const open = expandable && expanded.has(parent.id);
    const directIdentity = parent.subtypes?.length === 1 ? parent.subtypes[0] : parent;
    const parentButton = expandable
      ? `<button class="name-button hierarchy-toggle" type="button" data-stats-toggle="${parent.id}" aria-expanded="${open}"><span class="round-toggle">${open ? "−" : "+"}</span>${parent.name}</button>`
      : `<button class="name-button" type="button" data-deck-detail="${directIdentity.id}">${directIdentity.name}</button>`;
    const parentRow = statsRow(parent, parentButton, "");
    const parentDetail = !expandable && state.deckDetail === directIdentity.id
      ? statsDetailRow(directIdentity.id)
      : "";
    const subtypeRows = open ? parent.subtypes.map((subtype) => {
      const row = statsRow(
        subtype,
        `<button class="name-button" type="button" data-deck-detail="${subtype.id}">${subtype.name}</button>`,
        "subtype-row"
      );
      return row + (state.deckDetail === subtype.id ? statsDetailRow(subtype.id) : "");
    }).join("") : "";
    return parentRow + parentDetail + subtypeRows;
  }).join("");
}

function statsRow(record, name, rowClass) {
  return `<tr class="${rowClass}">
    <td>${name}</td>
    <td class="number">${avg(record.avg)}</td>
    <td class="number">${record.hs ?? 0}</td>
    <td class="number">${pct(record.hsShare)}</td>
    <td class="number">${record.top8 ?? 0}</td>
    <td class="number">${pct(record.top8Share)}</td>
    <td class="number">${pct(record.conversion)}</td>
  </tr>`;
}

function statsDetailRow(identity) {
  return `<tr class="deck-detail-row"><td colspan="7">${deckDetailHtml(identity, false)}</td></tr>`;
}

function chartHtml() {
  const chartRows = currentArchetypes().slice(0, 4).map((item) => `<div class="chart-row">
    <span>${item.name}</span>
    <div class="chart-bars">
      <div class="chart-bar hs" style="width:${Math.max(8, item.hsShare * 260)}px"><b>${pct(item.hsShare)}</b></div>
      <div class="chart-bar top8" style="width:${Math.max(8, item.top8Share * 260)}px"><b>${pct(item.top8Share)}</b></div>
    </div>
  </div>`).join("");
  return `<section class="panel chart-panel" aria-label="高分占比与八强占比图表">
    <div class="chart-legend"><span><i class="hs"></i>高分占比</span><span><i class="top8"></i>八强占比</span></div>
    ${chartRows}
  </section>`;
}

function statsView() {
  const hasExpanded = state.expandedStats.size > 0;
  const expandableParents = currentArchetypes().filter((item) => item.subtypes.length >= 2);
  const totals = state.format === "standard"
    ? { decks: 224, highScore: 97, top8: 56, observed: 97, theoretical: 103, rate: "94.2%" }
    : { decks: 416, highScore: 330, top8: 104, observed: 330, theoretical: 342, rate: "96.5%" };
  const sortHeader = (label, key, tip = "") => {
    const active = state.statsSortKey === key;
    const arrow = active ? (state.statsSortDirection === "desc" ? " ▼" : " ▲") : "";
    return `<button class="sort-button" type="button" data-stats-sort="${key}">${label}${arrow}</button>${tip ? infoTip(tip) : ""}`;
  };
  return `
    <section class="source-note">
      <p>本页面数据源为 MTGO 官网，官网仅放出各赛事前 32 的牌表，所以数据会有一定误差。整体 meta 占比误差较大，所以本页面不予展示，转而统计高分套牌数量。因为一方面高分套牌更有参考价值（会有更少情况被 0 胜随机套牌污染占比），另一方面高分套牌在前 32 中被囊括的比例也更大（不过超过 80 人左右的赛事中依旧会有高分套牌被 cut 掉）。</p>
      <p>套牌类型特征最后更新：2026-07-20　|　数据最后更新：2026-07-26</p>
    </section>
    ${rangeButtons(state.statsRange, "data-stats-range")}
    <div class="period-info">
      <span>统计区间：2026-07-13 ～ 2026-07-19　|　${totals.decks} 份牌表　|　高分 ${totals.highScore}　|　八强 ${totals.top8}</span>
      <strong>高分牌表完备度（原型示例）：实际收录 ${totals.observed} 份 / 理论应有 ${totals.theoretical} 份（${totals.rate}）</strong>
    </div>
    ${chartHtml()}
    <section class="panel">
      <div class="panel-toolbar">
        <h2>套牌统计</h2>
        ${expandableParents.length ? `<button id="stats-expand-all" class="secondary-button" type="button">${hasExpanded ? "隐藏全部 subtype" : "显示全部 subtype"}</button>` : ""}
      </div>
      <div class="table-scroll">
        <table class="data-table" style="width:980px;min-width:100%">
          ${fixedDataColumns(7)}
          <thead><tr>
            <th>${sortHeader("套牌", "name")}</th>
            <th class="number">${sortHeader("场均分", "avg", "该套牌对应瑞士轮理论轮数的平均得分，按总积分除以理论总轮数计算。范围 0–3 分，分数越高代表该套牌整体战绩越好。")}</th>
            <th class="number">${sortHeader("高分数量", "hs", "所选区间内该套牌打出高分成绩的数量。高分门槛随赛事轮数变化。")}</th>
            <th class="number">${sortHeader("高分占比", "hsShare", "所选区间内该套牌高分数量占总高分套牌数量的比例。")}</th>
            <th class="number">${sortHeader("八强数量", "top8", "所选区间内该套牌进入赛事前八名的数量。")}</th>
            <th class="number">${sortHeader("八强占比", "top8Share", "所选区间内该套牌八强数量占总八强数量的比例。")}</th>
            <th class="number">${sortHeader("转化率", "conversion", "所选区间内该套牌高分牌手中最终进入八强的比例。")}</th>
          </tr></thead>
          <tbody>${hierarchyRows(sortedStatsArchetypes(), state.expandedStats)}</tbody>
        </table>
      </div>
    </section>`;
}

function sortedStatsArchetypes() {
  const rows = [...currentArchetypes()];
  const key = state.statsSortKey;
  const direction = state.statsSortDirection === "asc" ? 1 : -1;
  rows.sort((left, right) => {
    const a = key === "name" ? left.name.toLowerCase() : (left[key] ?? -1);
    const b = key === "name" ? right.name.toLowerCase() : (right[key] ?? -1);
    if (a < b) return -1 * direction;
    if (a > b) return direction;
    return 0;
  });
  return rows;
}

function cardLink(name, quantity) {
  const search = `https://scryfall.com/search?q=${encodeURIComponent(`!"${name}"`)}`;
  const image = `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=image&version=normal`;
  return `<li><span class="qty">${quantity}</span><a class="card-link" href="${search}" target="_blank" rel="noopener" data-card-image="${image}">${name}</a></li>`;
}

function cardList(cards) {
  return `<ul class="card-list">${cards.map(([name, quantity]) => cardLink(name, quantity)).join("")}</ul>`;
}

function deckDetailName(id) {
  const flat = currentArchetypes().flatMap((parent) => [parent, ...(parent.subtypes || [])]);
  return flat.find((item) => item.id === id)?.name || id;
}

function deckDetailHtml(identity, exactDeck) {
  const name = typeof identity === "string" ? deckDetailName(identity) : identity.name;
  const cards = currentDeckCards();
  const exactMeta = typeof identity === "object" ? `<p class="deck-meta">${identity.event} · 第 ${identity.rank} 名 · ${identity.date}</p>` : `<p class="deck-meta">ExamplePlayer · 名次 2 · 积分 21 · 2026-07-19</p>`;
  const leftTitle = exactDeck ? "该赛事实际牌表" : "最佳牌表";
  const comparison = state.deckMode === "average"
    ? `<div class="change-box"><span>近期构筑变化度：</span><strong>7 分</strong><p>衡量本周构筑相对之前 4 周平均构筑的变化程度，数值越高说明本周构筑变动越大。</p></div>
       <h4 class="group-title core">核心组件</h4>${cardList(cards.average.slice(0, 4))}
       <h4 class="group-title flex">弹性组件</h4>${cardList(cards.average.slice(4))}`
    : `${exactMeta}<h4>主牌</h4>${cardList(cards.main.slice(0, 7))}<h4>备牌</h4>${cardList(cards.side.slice(0, 4))}`;
  const differences = state.format === "standard"
    ? { fewer: "Deadly Cover-Up 2（平均 2.8）", fewer2: "Duress 2（平均 2.6）", more: "Jeskai Revelation 4（平均 3.2）", more2: "Inevitable Defeat 4（平均 3.1）" }
    : { fewer: "Walking Ballista 1（平均 1.8）", fewer2: "Urza's Saga 3（平均 4.0）", more: "Unholy Heat 3（平均 1.2）", more2: "Haywire Mite 2（平均 0.7）" };
  return `<section class="deck-detail">
    <button id="close-deck-detail" class="deck-close" type="button" aria-label="关闭牌表">✕</button>
    <h3>${name}</h3>
    <div class="deck-columns">
      <div class="deck-column">
        <h4>${leftTitle}</h4>
        ${exactMeta}
        <div class="deviation-box">
          <span>偏离度：</span><strong>16 分</strong>
          <p>偏离度衡量该牌表与最近 4 周平均构筑的差异程度，数值越高越独创；不代表强弱。</p>
          <div class="difference-grid">
            <div><b>比平均少带</b><p>${differences.fewer}</p><p>${differences.fewer2}</p></div>
            <div><b>比平均多带</b><p>${differences.more}</p><p>${differences.more2}</p></div>
          </div>
        </div>
        <h4>主牌</h4>${cardList(cards.main)}
        <h4>备牌</h4>${cardList(cards.side)}
      </div>
      <div class="deck-column">
        <div class="deck-mode" role="group" aria-label="平均构筑与典型牌表">
          <button type="button" data-deck-mode="average" class="${state.deckMode === "average" ? "active" : ""}">近4周平均构筑</button>
          <button type="button" data-deck-mode="typical" class="${state.deckMode === "typical" ? "active" : ""}">实际典型牌表</button>
          <span>（样本 42）</span>
        </div>
        ${comparison}
      </div>
    </div>
  </section>`;
}

function expandedAxisNodes(expandedSet) {
  return currentMatchupParents().flatMap((parent) => {
    if (parent.subtypes.length >= 2 && expandedSet.has(parent.id)) {
      return [
        { id: parent.id, parentId: parent.id, name: parent.name, subtype: false, first: true },
        ...parent.subtypes.map((name, index) => ({ id: `${parent.id}-${index}`, parentId: parent.id, name, subtype: true, first: false })),
      ];
    }
    return [{ id: parent.id, parentId: parent.id, name: parent.name, subtype: false, first: true }];
  });
}

function matrixRecordValue(wins, losses, draws, mirror = false) {
  const matches = wins + losses + draws;
  const rate = wins / matches;
  const z = 1.96;
  const denominator = 1 + (z * z / matches);
  const ci = z * Math.sqrt((rate * (1 - rate) / matches) + (z * z / (4 * matches * matches))) / denominator;
  return { wins, losses, draws, matches, rate: rate * 100, ci: ci * 100, mirror };
}

function matrixValue(rowIndex, columnIndex, rowId = null, columnId = null, scope = "mtgo") {
  if (rowId && rowId === columnId) {
    const seed = Array.from(rowId).reduce((sum, character) => sum + character.charCodeAt(0), 0);
    const wins = 10 + (seed % 9);
    const draws = scope === "tabletop" ? 2 * (1 + (seed % 3)) : 0;
    return matrixRecordValue(wins, wins, draws, true);
  }
  const matches = 18 + ((rowIndex * 17 + columnIndex * 11) % 58);
  const draws = scope === "tabletop" ? ((rowIndex + columnIndex) % 4) : 0;
  const targetRate = 42 + ((rowIndex * 13 + columnIndex * 7) % 18);
  const wins = Math.min(matches - draws, Math.round(matches * targetRate / 100));
  return matrixRecordValue(wins, matches - wins - draws, draws);
}

function matrixCell(value) {
  if (!value) return `<td class="matrix-cell na">—</td>`;
  const style = value.rate >= 53 ? "good" : value.rate <= 47 ? "bad" : "even";
  const low = value.matches < 25 ? "low-sample" : "";
  const record = `${value.wins}-${value.losses}-${value.draws}（${value.matches}）`;
  const mirrorLabel = value.mirror ? " · 内战" : "";
  return `<td class="matrix-cell ${style} ${low}" tabindex="0" data-record="${record}" title="胜-负-平：${record}${mirrorLabel}"><strong>${value.rate.toFixed(1)}</strong><small>±${value.ci.toFixed(1)}</small></td>`;
}

function matrixHtml(scope = "mtgo") {
  const rows = expandedAxisNodes(state.matchupRows);
  const columns = expandedAxisNodes(state.matchupColumns);
  const rowIndex = new Map(rows.map((row, index) => [row.id, index]));
  const columnIndex = new Map(columns.map((column, index) => [column.id, index]));
  return `<div class="table-scroll matrix-scroll"><table class="matchup-table">
    <thead><tr><th class="corner"></th><th class="column-head overall">整体</th>${columns.map((column) => {
      const expanded = state.matchupColumns.has(column.parentId);
      const canToggle = currentMatchupParents().find((parent) => parent.id === column.parentId)?.subtypes.length >= 2;
      const toggle = canToggle && column.first ? `<button type="button" class="axis-toggle column-toggle" data-matchup-column="${column.parentId}" aria-label="${expanded ? "收起" : "展开"}${column.name}">${expanded ? "−" : "+"}</button>` : "";
      return `<th class="column-head ${column.subtype ? "subtype-head" : ""}"><div>${toggle}<span>${column.name}</span></div></th>`;
    }).join("")}</tr></thead>
    <tbody>${rows.map((row) => {
      const expanded = state.matchupRows.has(row.parentId);
      const canToggle = currentMatchupParents().find((parent) => parent.id === row.parentId)?.subtypes.length >= 2;
      const toggle = canToggle && row.first ? `<button type="button" class="axis-toggle" data-matchup-row="${row.parentId}" aria-label="${expanded ? "收起" : "展开"}${row.name}">${expanded ? "−" : "+"}</button>` : "";
      const overall = matrixCell(matrixValue(rowIndex.get(row.id), columns.length + 1, null, null, scope));
       return `<tr><th class="row-head ${row.subtype ? "subtype-head" : ""}">${toggle}<span>${row.name}</span></th>${overall}${columns.map((column) => matrixCell(matrixValue(rowIndex.get(row.id), columnIndex.get(column.id), row.id, column.id, scope))).join("")}</tr>`;
    }).join("")}</tbody>
  </table></div><div id="matrix-record" class="matrix-record" role="status" hidden></div>`;
}

function matchupLegend() {
  return `<div class="matchup-legend">
    <span>胜率配色：</span>
    <div><div class="legend-bar"></div><div class="legend-values"><span>0%</span><span>50%</span><span>100%</span></div></div>
    <span><i class="na-chip"></i>无数据/样本不足</span>
    <span><i class="low-chip"></i>低样本（谨慎参考）</span>
  </div>`;
}

function matchupView() {
  const expanded = state.matchupRows.size || state.matchupColumns.size;
  return `
    ${rangeButtons(state.matchupRange, "data-matchup-range")}
    <section class="source-note">
      <p>数据来自 Videre 众包对局记录，以官方公开牌表分类；因官方仅公开前32牌表，对局数据并不包含全体参赛者。矩阵内数值为行套牌对列套牌的对局胜率，按胜场数÷有效对局数计算；正常平局计入分母但不计入胜场。对角线显示真实内战胜率，内战也计入“整体”。大字为胜率，小字为 95% 置信区间半宽（±范围），样本越多区间越窄。悬停或点击查看具体战绩。</p>
      <p><strong>Videre赛事覆盖率（原型示例）：应收录 27 场，实际有可用对局档案 25 场（92.6%）；另有 1 场延后、1 场缺失。</strong></p>
    </section>
    <section class="panel">
      <div class="panel-toolbar">
        <h2>对阵胜率</h2>
        <button id="matchup-expand-all" class="secondary-button" type="button">${expanded ? "收起全部 subtype" : "展开全部 subtype"}</button>
      </div>
      ${matchupLegend()}
      ${matrixHtml("mtgo")}
    </section>`;
}

function top8View() {
  const events = currentTop8Events();
  const selected = typeof state.deckDetail === "object" ? state.deckDetail : null;
  const selectedEvent = selected ? events[selected.eventIndex] : null;
  const top8ShortName = (name) => name
    .replace(/^(Modern|Standard)\s+/, "")
    .replace("Showcase Qualifier", "SCQ")
    .replace("Showcase Challenge", "SC")
    .replace("RC Super Qualifier", "RCSQ")
    .replace("RC Qualifier", "RCQ")
    .replace("Challenge", "C");
  return `
    <section class="source-note">
      <p>数据来源：MTGO 官网公开赛事牌表。按完整自然周列出该周收录赛事的前八名牌表。</p>
    </section>
    <div class="select-row">
      <label for="top8-week">显示周：</label>
      <select id="top8-week">${top8Weeks.map((week) => `<option value="${week.value}" ${state.top8Week === week.value ? "selected" : ""}>${week.label}</option>`).join("")}</select>
    </div>
    <section class="panel">
      <div class="table-scroll"><table class="top8-table top8-week-table">
        <thead><tr>
          <th>名次</th>
          ${events.map((event) => `<th title="${event.name}"><strong>${top8ShortName(event.name)}</strong><small>${event.date} · ${event.players} 人</small></th>`).join("")}
        </tr></thead>
        <tbody>${Array.from({ length: 8 }, (_, rankIndex) => `<tr>
          <td>${rankIndex + 1}</td>
          ${events.map((event, eventIndex) => `<td><button class="name-button" type="button" data-top8-detail="${eventIndex}:${rankIndex}">${event.decks[rankIndex]}</button></td>`).join("")}
        </tr>`).join("")}</tbody>
      </table></div>
      ${selectedEvent ? deckDetailHtml({
        name: selectedEvent.decks[selected.rankIndex],
        event: selectedEvent.name,
        rank: selected.rankIndex + 1,
        date: selectedEvent.date,
      }, true) : ""}
    </section>`;
}

const tabletopTips = {
  count: "当前赛事和统计范围内纳入统计的牌表数量。同一牌手跨第一日和第二日时不重复计算牌表身份。",
  share: "该套牌类型牌表数占当前统计人群全部有效牌表的比例。未能分类的牌表仍保留在总体分母中。",
  day2Share: "该套牌类型在第二日参赛牌表中的比例。对于混合赛，它只描述入围人群，不代表纯构筑晋级能力。",
  avg: "构筑赛总积分除以有效理论构筑轮数。正常退赛不会减少理论轮数；经确认的八强锁定豁免轮次会从分母中移除。轮抽积分不计入。",
  high: "在当前阶段中，构筑积分严格超过理论最高积分一半的牌表数量。高分线按可取得的三分胜场档位向上取整。",
  highShare: "该套牌类型的高分牌表数占当前阶段全部高分牌表的比例。它回答“高分区中有多少属于该套牌”。",
  highRate: "该套牌类型达到高分线的牌表数除以该类型在当前阶段的全部牌表数。它回答“该套牌有多大比例进入高分区”。",
  day2HighRate: "该套牌类型在第二日达到第二日高分线的牌表数除以该类型的第二日牌表数。",
  conversion: "该套牌类型进入第二日的人数除以该类型第一日初始牌表数。只用于晋级完全由同一构筑赛事成绩决定的赛事。",
  record: "用于胜率的胜—负—和记录，包含同一套牌类型内战。正常平局计入有效对局但不计入胜场；轮空、约和、未到场、官方判胜、轮抽及淘汰赛均不计入。",
  winRate: "胜场数÷（胜场数＋负场数＋正常平局数）。主要胜率包含同一套牌类型内战，并与战绩和有效对局数一起显示。",
  day1WinRate: "只使用第一日真实构筑赛对局并包含同一套牌类型内战，较接近初始参赛人群，但可能受到早期退赛影响。正常平局计入分母但不计入胜场。",
  matches: "实际用于旁列胜率计算的真实构筑赛对局数，包含同一套牌类型内战。",
  completion: "已完成或获得官方豁免的理论构筑轮数占全部应进行理论构筑轮数的比例。退赛后未进行的轮次会降低完赛率。",
};

function currentTabletopEvent() {
  return tabletopEvents.find((event) => event.id === state.tabletopEvent) || tabletopEvents[0];
}

function selectedTabletopEvents() {
  return tabletopEvents.filter((event) => state.tabletopSelectedEvents.has(event.id));
}

function tabletopAvailableScopes() {
  const events = state.tabletopView === "overview" ? [currentTabletopEvent()] : selectedTabletopEvents();
  return ["day1", "day2", "all_constructed"].filter((scope) => events.every((event) => event.scopes.includes(scope)));
}

function tabletopScopeLabel(scope) {
  return {
    day1: "第一日摩登",
    day2: "第二日摩登",
    all_constructed: "全部摩登瑞士轮",
  }[scope];
}

function tabletopEventSelector() {
  if (state.tabletopView === "overview") {
    return `<div class="tabletop-event-select">
      <label for="tabletop-event">赛事：</label>
      <select id="tabletop-event">${tabletopEvents.map((event) => `<option value="${event.id}" ${state.tabletopEvent === event.id ? "selected" : ""}>${event.name}</option>`).join("")}</select>
    </div>`;
  }
  return `<div class="event-checkbox-pane" role="group" aria-label="选择用于对阵胜率的赛事">
    ${tabletopEvents.map((event) => `<label>
      <input type="checkbox" data-tabletop-event-check="${event.id}" ${state.tabletopSelectedEvents.has(event.id) ? "checked" : ""}>
      <span><strong>${event.name}</strong><small>${event.date} · ${event.structureLabel}${event.prototype ? " · 原型数据" : ""}</small></span>
    </label>`).join("")}
  </div>`;
}

function tabletopScopeControls() {
  const available = tabletopAvailableScopes();
  return `<div class="scope-tabs" role="group" aria-label="统计范围">
    ${["day1", "day2", "all_constructed"].map((scope) => {
      const enabled = available.includes(scope);
      return `<button type="button" data-tabletop-scope="${scope}" class="${state.tabletopScope === scope ? "active" : ""}" ${enabled ? "" : 'disabled title="所选赛事没有共同的这一统计范围"'}>${tabletopScopeLabel(scope)}</button>`;
    }).join("")}
  </div>`;
}

function tabletopScopeDescription() {
  const selected = selectedTabletopEvents();
  const event = state.tabletopView === "matchup" && selected.length === 1 ? selected[0] : currentTabletopEvent();
  if (state.tabletopView === "matchup" && selected.length > 1) {
    return `<div class="selection-warning">所选赛事先合计当前范围的原始胜—负—和记录，再计算合并胜率；不会平均各赛事百分比。包含无 Cut 单阶段赛事时，只能使用全部摩登瑞士轮。</div>`;
  }
  if (state.tabletopScope === "day1") {
    return `<div class="selection-warning">${event.structure === "mixed" ? "仅统计第一日的摩登瑞士轮；轮抽积分和对局完全排除。" : "统计完整第一日构筑瑞士轮；普通退赛后的未进行轮次仍保留在理论轮数中。"}该范围覆盖较广的初始人群，但早期退赛可能减少实际对局样本。</div>`;
  }
  if (state.tabletopScope === "day2") {
    return `<div class="selection-warning">${event.structure === "mixed"
      ? "第二日参赛者由包含轮抽成绩在内的综合赛事表现筛选；第二日摩登统计描述入围人群，存在选拔偏差，不能解释为纯摩登晋级能力。"
      : "第二日牌手由同一场构筑赛事的第一日成绩筛选，因此可以计算晋级率；数据仍描述筛选后的较强人群，需结合样本数和完赛情况解读。"}</div>`;
  }
  if (event.structure === "constructed_single_stage") {
    return `<div class="selection-warning">本赛事没有独立第二日参赛人群。所有主要瑞士轮作为同一个统计范围处理，并使用高分区描述成绩较好的牌表。</div>`;
  }
  return `<div class="selection-warning">合计第一日和第二日的真实摩登瑞士轮记录。未晋级牌手不会获得第二日理论轮数；样本较大，但第二日牌手经过筛选，因此不能视为对初始人群的无偏估计。合并范围不生成高分指标。</div>`;
}

function tabletopEventSummary() {
  if (state.tabletopView === "matchup") {
    const events = selectedTabletopEvents();
    return `<section class="panel event-summary">
      <div class="event-title-row"><strong>已选 ${events.length} 场赛事</strong><span>${events.map((event) => event.name).join("、")}</span></div>
      <p>对阵胜率仅合并同一赛制、当前共同统计范围内的真实构筑瑞士轮记录。原型赛事仅用于验证交互。</p>
    </section>`;
  }
  const event = currentTabletopEvent();
  return `<section class="panel event-summary">
    <div class="event-title-row">
      <strong>${event.name}</strong>
      ${event.sourceUrl ? `<a href="${event.sourceUrl}" target="_blank" rel="noopener">查看赛事来源</a>` : '<span class="prototype-badge">原型数据</span>'}
    </div>
    <p>${event.date} · ${event.structureLabel} · ${event.detail}</p>
    <div class="quality-notice"><strong>${event.prototype ? "原型说明" : "数据质量：警告"}</strong><span>${event.quality}</span></div>
  </section>`;
}

function tabletopScopeSummary() {
  if (state.tabletopView === "matchup") {
    const events = selectedTabletopEvents();
    const summaries = events.map((event) => event.summaries[state.tabletopScope]);
    const items = [
      ["已选赛事", events.length],
      ["参赛人次", summaries.reduce((sum, item) => sum + item.participants, 0).toLocaleString()],
      ["有效对局", summaries.reduce((sum, item) => sum + item.matches, 0).toLocaleString()],
      ["原型赛事", events.filter((event) => event.prototype).length],
    ];
    return `<div class="summary-grid">${items.map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("")}</div>`;
  }
  const summary = currentTabletopEvent().summaries[state.tabletopScope];
  const items = [
    [state.tabletopScope === "day2" ? "第二日人数" : "参赛人数", summary.participants],
    ["已分类牌表", summary.known],
    ["有效摩登对局", summary.matches.toLocaleString()],
    ["未知分类", summary.unknown],
  ];
  return `<div class="summary-grid">${items.map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("")}</div>`;
}

function boundedRate(value) {
  return Math.max(0, Math.min(1, value));
}

function recordWinRate(record) {
  const [wins, losses, draws] = record.split("-").map(Number);
  return wins / (wins + losses + draws);
}

function tabletopRecordForScope(record, event, scope, summary) {
  const scopeAdjustment = scope === "day2" ? 0.025 : scope === "all_constructed" ? 0.010 : 0;
  const eventAdjustment = event.structure === "constructed_day2" ? 0.012 : event.structure === "constructed_single_stage" ? 0.020 : 0;
  const count = Math.max(0, Math.round(summary.participants * record.share));
  const targetWinRate = boundedRate(record.winRate + scopeAdjustment + eventAdjustment);
  const matches = Math.max(1, Math.round(summary.matches * record.share * 1.8));
  const draws = Math.round(matches * 0.03);
  const wins = Math.min(matches - draws, Math.round(matches * targetWinRate));
  const winRate = wins / matches;
  const highRate = boundedRate(record.highRate + scopeAdjustment);
  const high = summary.high === null ? null : Math.round(count * highRate);
  return {
    ...record,
    count,
    avg: record.avg + scopeAdjustment + eventAdjustment,
    winRate,
    day1WinRate: boundedRate(record.winRate + eventAdjustment),
    completion: boundedRate(record.completion + summary.completion - 0.959),
    high,
    highShare: summary.high ? high / summary.high : null,
    highRate,
    matches,
    record: `${wins}-${Math.max(0, matches - wins - draws)}-${draws}`,
    day2Conversion: event.structure === "constructed_day2" && scope === "day2"
      ? boundedRate((summary.day2Conversion || 0) + (winRate - 0.5) * 0.18)
      : null,
    subtypes: (record.subtypes || []).map((subtype) => tabletopRecordForScope(subtype, event, scope, summary)),
  };
}

function tabletopOverallRow(event, scope, summary) {
  const winRate = recordWinRate(summary.record);
  const day1WinRate = event.summaries.day1 ? recordWinRate(event.summaries.day1.record) : winRate;
  return {
    id: "overall",
    name: "整体",
    overall: true,
    count: summary.participants,
    share: 1,
    avg: summary.avg,
    winRate,
    day1WinRate,
    completion: summary.completion,
    high: summary.high,
    highShare: summary.high === null ? null : 1,
    highRate: summary.high === null ? null : summary.high / summary.participants,
    matches: summary.matches,
    record: summary.record,
    day2Conversion: event.structure === "constructed_day2" && scope === "day2" ? summary.day2Conversion : null,
    subtypes: [],
  };
}

function tabletopColumns(event, scope) {
  const columns = [
    { key: "name", label: "套牌类型", tip: "" },
    { key: "count", label: "牌表数", tip: tabletopTips.count },
    { key: "share", label: scope === "day2" ? "第二日占比" : "环境占比", tip: scope === "day2" ? tabletopTips.day2Share : tabletopTips.share },
    { key: "avg", label: "场均分", tip: tabletopTips.avg },
  ];
  if (event.structure === "constructed_day2" && scope === "day2") {
    columns.push({ key: "day2Conversion", label: "晋级率", tip: tabletopTips.conversion });
  }
  const highScoreAvailable = scope !== "all_constructed" || event.structure === "constructed_single_stage";
  if (highScoreAvailable) {
    columns.push(
      { key: "high", label: "高分牌表", tip: tabletopTips.high },
      { key: "highShare", label: "高分占比", tip: tabletopTips.highShare },
      { key: "highRate", label: scope === "day2" ? "第二日高分率" : "高分达成率", tip: scope === "day2" ? tabletopTips.day2HighRate : tabletopTips.highRate }
    );
  }
  if (scope === "all_constructed" && event.structure !== "constructed_single_stage") {
    columns.push({ key: "day1WinRate", label: "第一日对局胜率", tip: tabletopTips.day1WinRate });
  }
  columns.push(
    { key: "record", label: "对局战绩 / 胜率", tip: `${tabletopTips.record}${tabletopTips.winRate}` },
    { key: "matches", label: "有效对局", tip: tabletopTips.matches },
    { key: "completion", label: "完赛率", tip: tabletopTips.completion }
  );
  return columns;
}

function tabletopCell(record, key) {
  if (key === "name") return record.name;
  if (key === "count" || key === "high" || key === "matches") return record[key] ?? "—";
  if (key === "avg") return avg(record.avg);
  if (["share", "highShare", "highRate", "day2Conversion", "day1WinRate", "completion"].includes(key)) return pct(record[key]);
  if (key === "record") return `<span class="record-cell"><strong>${record.record}</strong><small>${pct(record.winRate)}</small></span>`;
  return record[key] ?? "—";
}

function tabletopMetricHeader(column) {
  return `${column.label}${column.tip ? infoTip(column.tip) : ""}`;
}

function tabletopRow(record, name, rowClass, columns) {
  return `<tr class="${rowClass}">${columns.map((column) => `<${column.key === "name" ? "td" : 'td class="number"'}>${column.key === "name" ? name : tabletopCell(record, column.key)}</td>`).join("")}</tr>`;
}

function tabletopOverview() {
  const event = currentTabletopEvent();
  const summary = event.summaries[state.tabletopScope];
  const columns = tabletopColumns(event, state.tabletopScope);
  const rows = tabletopRows.map((record) => tabletopRecordForScope(record, event, state.tabletopScope, summary));
  const overall = tabletopOverallRow(event, state.tabletopScope, summary);
  return `<div class="panel-toolbar">
      <h2>套牌表现概览</h2>
      <button id="tabletop-expand-all" class="secondary-button" type="button">${state.tabletopExpanded.size ? "隐藏全部 subtype" : "显示全部 subtype"}</button>
    </div>
    <div class="table-scroll"><table class="data-table tabletop-table" style="width:${260 + ((columns.length - 1) * 120)}px;min-width:100%">
      ${fixedDataColumns(columns.length)}
      <thead><tr>${columns.map((column) => `<th class="${column.key === "name" ? "" : "number"}">${tabletopMetricHeader(column)}</th>`).join("")}</tr></thead>
      <tbody>
        ${tabletopRow(overall, "整体", "overall-row", columns)}
        ${rows.flatMap((parent) => {
          const expandable = parent.subtypes.length >= 2;
          const open = expandable && state.tabletopExpanded.has(parent.id);
          const parentName = expandable ? `<button class="name-button hierarchy-toggle" type="button" data-tabletop-toggle="${parent.id}"><span class="round-toggle">${open ? "−" : "+"}</span>${parent.name}</button>` : parent.name;
          const row = tabletopRow(parent, parentName, "", columns);
          const subtypes = open ? parent.subtypes.map((subtype) => tabletopRow(subtype, subtype.name, "subtype-row", columns)).join("") : "";
          return row + subtypes;
        }).join("")}
      </tbody>
    </table></div>`;
}

function tabletopMatchup() {
  const selected = selectedTabletopEvents();
  return `<div class="panel-toolbar">
      <div><h2>赛事对阵胜率</h2><p class="panel-subtitle">${selected.length === 1 ? selected[0].name : `合并 ${selected.length} 场赛事`} · ${tabletopScopeLabel(state.tabletopScope)}</p></div>
      <button id="matchup-expand-all" class="secondary-button" type="button">${state.matchupRows.size || state.matchupColumns.size ? "收起全部 subtype" : "展开全部 subtype"}</button>
    </div>
    ${matchupLegend()}
    ${matrixHtml("tabletop")}`;
}

function tabletopView() {
  return `
    <div class="tabletop-view-tabs subview-tabs" role="group" aria-label="实体大赛视图">
      <button type="button" data-tabletop-view="overview" class="${state.tabletopView === "overview" ? "active" : ""}">赛事概览</button>
      <button type="button" data-tabletop-view="matchup" class="${state.tabletopView === "matchup" ? "active" : ""}">对阵胜率</button>
    </div>
    ${tabletopEventSelector()}
    ${tabletopScopeControls()}
    ${tabletopScopeDescription()}
    ${tabletopEventSummary()}
    ${tabletopScopeSummary()}
    <section class="panel">${state.tabletopView === "overview" ? tabletopOverview() : tabletopMatchup()}</section>`;
}

function pickupView() {
  return `<div class="pickup-layout">
    <aside class="pickup-weeks"><h2>往期</h2>${pickupWeeks.map((week) => `<button type="button" data-pickup-week="${week.id}" class="${state.pickupWeek === week.id ? "active" : ""}">${week.label}<span>${week.range}</span></button>`).join("")}</aside>
    <div class="pickup-content">${pickupGroups.map((group) => `<section class="pickup-group"><h2>${group.title}</h2>${group.items.length ? group.items.map((item) => {
      const open = state.pickupOpen.has(item.id);
      return `<article class="pickup-card ${open ? "open" : ""}">
        <button type="button" class="pickup-head" data-pickup-toggle="${item.id}" aria-expanded="${open}">
          <span><strong>${item.name}</strong><small>${item.player} · 名次 ${item.rank} · 积分 ${item.score} · ${item.date}</small></span>
          <b>偏离度 ${item.deviation} 分</b>
        </button>
        ${open ? `<div class="pickup-body"><p>${item.comment}</p><div class="deck-columns"><div class="deck-column"><h4>主牌</h4>${cardList(item.main)}</div><div class="deck-column"><h4>备牌</h4>${cardList(item.side)}</div></div></div>` : ""}
      </article>`;
    }).join("") : '<p class="pickup-empty">本周空缺</p>'}</section>`).join("")}</div>
  </div>`;
}

function bindCommonInteractions() {
  document.querySelectorAll("[data-stats-range]").forEach((button) => button.addEventListener("click", () => {
    state.statsRange = Number(button.dataset.statsRange);
    state.deckDetail = null;
    renderView();
  }));
  document.querySelectorAll("[data-matchup-range]").forEach((button) => button.addEventListener("click", () => {
    state.matchupRange = Number(button.dataset.matchupRange);
    renderView();
  }));
  document.querySelectorAll("[data-stats-toggle]").forEach((button) => button.addEventListener("click", () => {
    toggleSet(state.expandedStats, button.dataset.statsToggle);
    state.deckDetail = null;
    renderView();
  }));
  document.querySelectorAll("[data-stats-sort]").forEach((button) => button.addEventListener("click", () => {
    const key = button.dataset.statsSort;
    if (state.statsSortKey === key) state.statsSortDirection = state.statsSortDirection === "desc" ? "asc" : "desc";
    else {
      state.statsSortKey = key;
      state.statsSortDirection = key === "name" ? "asc" : "desc";
    }
    renderView();
  }));
  document.querySelector("#stats-expand-all")?.addEventListener("click", () => {
    if (state.expandedStats.size) state.expandedStats.clear();
    else currentArchetypes().filter((item) => item.subtypes.length >= 2).forEach((item) => state.expandedStats.add(item.id));
    state.deckDetail = null;
    renderView();
  });
  document.querySelectorAll("[data-deck-detail]").forEach((button) => button.addEventListener("click", () => {
    state.deckDetail = button.dataset.deckDetail;
    state.deckMode = "average";
    renderView();
  }));
  document.querySelector("#close-deck-detail")?.addEventListener("click", () => {
    state.deckDetail = null;
    renderView();
  });
  document.querySelectorAll("[data-deck-mode]").forEach((button) => button.addEventListener("click", () => {
    state.deckMode = button.dataset.deckMode;
    renderView();
  }));
  document.querySelectorAll("[data-matchup-row]").forEach((button) => button.addEventListener("click", () => {
    toggleSet(state.matchupRows, button.dataset.matchupRow);
    renderView();
  }));
  document.querySelectorAll("[data-matchup-column]").forEach((button) => button.addEventListener("click", () => {
    toggleSet(state.matchupColumns, button.dataset.matchupColumn);
    renderView();
  }));
  document.querySelector("#matchup-expand-all")?.addEventListener("click", () => {
    const eligible = currentMatchupParents().filter((parent) => parent.subtypes.length >= 2).map((parent) => parent.id);
    if (state.matchupRows.size || state.matchupColumns.size) {
      state.matchupRows.clear();
      state.matchupColumns.clear();
    } else {
      eligible.forEach((id) => {
        state.matchupRows.add(id);
        state.matchupColumns.add(id);
      });
    }
    renderView();
  });
  document.querySelectorAll("[data-record]").forEach((cell) => {
    const showRecord = () => {
      const popover = document.querySelector("#matrix-record");
      if (!popover) return;
      popover.textContent = `胜-负-平：${cell.dataset.record}`;
      popover.hidden = false;
    };
    cell.addEventListener("mouseenter", showRecord);
    cell.addEventListener("focus", showRecord);
    cell.addEventListener("click", showRecord);
    cell.addEventListener("mouseleave", () => {
      const popover = document.querySelector("#matrix-record");
      if (popover) popover.hidden = true;
    });
  });
  document.querySelector("#top8-week")?.addEventListener("change", (event) => {
    state.top8Week = event.target.value;
    state.deckDetail = null;
    renderView();
  });
  document.querySelectorAll("[data-top8-detail]").forEach((button) => button.addEventListener("click", () => {
    const [eventIndex, rankIndex] = button.dataset.top8Detail.split(":").map(Number);
    state.deckDetail = { eventIndex, rankIndex };
    state.deckMode = "average";
    renderView();
  }));
  document.querySelectorAll("[data-tabletop-scope]").forEach((button) => button.addEventListener("click", () => {
    if (button.disabled) return;
    state.tabletopScope = button.dataset.tabletopScope;
    renderView();
  }));
  document.querySelectorAll("[data-tabletop-view]").forEach((button) => button.addEventListener("click", () => {
    const nextView = button.dataset.tabletopView;
    if (nextView === "matchup") {
      state.tabletopSelectedEvents.add(state.tabletopEvent);
    } else {
      const latest = selectedTabletopEvents().sort((left, right) => right.sortDate.localeCompare(left.sortDate))[0];
      if (latest) state.tabletopEvent = latest.id;
    }
    state.tabletopView = nextView;
    if (!tabletopAvailableScopes().includes(state.tabletopScope)) state.tabletopScope = "all_constructed";
    state.tabletopExpanded.clear();
    renderView();
  }));
  document.querySelector("#tabletop-event")?.addEventListener("change", (event) => {
    state.tabletopEvent = event.target.value;
    if (!tabletopAvailableScopes().includes(state.tabletopScope)) state.tabletopScope = "all_constructed";
    state.tabletopExpanded.clear();
    renderView();
  });
  document.querySelectorAll("[data-tabletop-event-check]").forEach((checkbox) => checkbox.addEventListener("change", () => {
    const eventId = checkbox.dataset.tabletopEventCheck;
    if (checkbox.checked) state.tabletopSelectedEvents.add(eventId);
    else if (state.tabletopSelectedEvents.size > 1) state.tabletopSelectedEvents.delete(eventId);
    if (!tabletopAvailableScopes().includes(state.tabletopScope)) state.tabletopScope = "all_constructed";
    renderView();
  }));
  document.querySelectorAll("[data-tabletop-toggle]").forEach((button) => button.addEventListener("click", () => {
    toggleSet(state.tabletopExpanded, button.dataset.tabletopToggle);
    renderView();
  }));
  document.querySelector("#tabletop-expand-all")?.addEventListener("click", () => {
    if (state.tabletopExpanded.size) state.tabletopExpanded.clear();
    else tabletopRows.filter((row) => row.subtypes.length >= 2).forEach((row) => state.tabletopExpanded.add(row.id));
    renderView();
  });
  document.querySelectorAll("[data-pickup-week]").forEach((button) => button.addEventListener("click", () => {
    state.pickupWeek = button.dataset.pickupWeek;
    state.pickupOpen.clear();
    renderView();
  }));
  document.querySelectorAll("[data-pickup-toggle]").forEach((button) => button.addEventListener("click", () => {
    toggleSet(state.pickupOpen, button.dataset.pickupToggle);
    renderView();
  }));
  bindCardPreviews();
}

function toggleSet(set, value) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
}

function bindCardPreviews() {
  const preview = document.querySelector("#card-preview");
  document.querySelectorAll("[data-card-image]").forEach((link) => {
    link.addEventListener("mouseenter", (event) => {
      preview.src = link.dataset.cardImage;
      preview.style.display = "block";
      moveCardPreview(event);
    });
    link.addEventListener("mousemove", moveCardPreview);
    link.addEventListener("mouseleave", () => {
      preview.style.display = "none";
      preview.removeAttribute("src");
    });
  });
}

function moveCardPreview(event) {
  const preview = document.querySelector("#card-preview");
  preview.style.left = `${Math.min(window.innerWidth - 255, event.clientX + 16)}px`;
  preview.style.top = `${Math.max(8, Math.min(window.innerHeight - 345, event.clientY + 16))}px`;
}

function renderView() {
  const root = document.querySelector("#view");
  if (state.product === "stats") root.innerHTML = statsView();
  else if (state.product === "matchup") root.innerHTML = matchupView();
  else if (state.product === "top8") root.innerHTML = top8View();
  else if (state.product === "tabletop") root.innerHTML = tabletopView();
  else root.innerHTML = pickupView();
  bindCommonInteractions();
}

function render() {
  renderNavigation();
  renderView();
}

document.querySelector("#lang-zh").addEventListener("click", () => {
  document.querySelector("#lang-zh").classList.add("active");
  document.querySelector("#lang-en").classList.remove("active");
  showAvailabilityMessage("");
});
document.querySelector("#lang-en").addEventListener("click", () => {
  document.querySelector("#lang-zh").classList.add("active");
  document.querySelector("#lang-en").classList.remove("active");
  showAvailabilityMessage("本轮先确认中文界面；英文文案将在中文定稿后另行提交确认。");
});

render();
