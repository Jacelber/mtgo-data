// ===================== Configuration =====================
const CHART_MIN_SHARE = 0.02;
const RANGES = [1, 4, 12, 36];
const FORMATS = [
  { key: "standard", enabled: true },
  { key: "pioneer",  enabled: false },
  { key: "modern",   enabled: true },
];
const DIFF_MIN = 1;   // Show only cards where |deck_qty - typical_qty| >= 1.

// ===================== Localization dictionary =====================
const I18N = {
  zh: {
    siteTitle: "MTG Meta数据分析",
    range_1w: "1 周", range_4w: "4 周", range_12w: "12 周", range_36w: "36 周",
    format_standard: "标准", format_pioneer: "先驱", format_modern: "摩登",
    col_archetype: "套牌", col_appr: "场均分", col_hs_count: "高分数量", col_hs_share: "高分占比",
    col_t8_count: "八强数量", col_t8_share: "八强占比", col_conv: "转化率",
    chart_hs: "高分占比", chart_t8: "八强占比",
    period: "统计区间", loading: "加载中…",
    best_deck: "最佳牌表",
    main_deck: "主牌", side_deck: "备牌", na: "N/A", others:"其他",
    tab_synthetic: "近4周平均构筑", tab_real: "实际典型牌表",
    core_group: "核心组件", flex_group: "弹性组件",
    avg_sample: "样本",
    avg_none: "4 周样本不足，无平均牌表",
    dev_title: "偏离度", dev_suffix: " 分",
    dev_desc: "偏离度衡量该牌表与最近 4 周平均构筑的差异程度，数值越高越独创；不代表强弱。",
    diff_fewer: "比平均少带", diff_more: "比平均多带",
    typical_qty: "平均",
    change_title: "近期构筑变化度", change_suffix: " 分",
    change_desc: "衡量本周构筑相对之前 4 周平均构筑的变化程度，数值越高说明本周构筑变动越大。",
    change_note_recent: "本周样本不足，暂无变化度",
    change_note_prior: "缺少历史构筑数据，无法计算变化度",
    change_note_nobase: "4 周样本不足，暂无变化度",
    view_stats: "MTGO官方数据统计", view_pickup: "每周精选套牌",
    pickup_weeks: "往期", pickup_existing: "新科技",
    pickup_new: "新套牌", pickup_empty: "本周空缺",
    pickup_no_data: "暂无每周精选内容",
    pk_rank: "名次", pk_score: "积分",
    view_matchup: "对阵胜率",
    mx_overall: "整体",
    mx_wld: "胜-负-平",
    mx_na: "无数据/样本不足",
    mx_low_sample: "低样本（谨慎参考）",
    mx_expand_all: "展开全部 subtype",
    mx_collapse_all: "收起全部 subtype",
    mx_expand_row: "展开行 subtype",
    mx_collapse_row: "收起行 subtype",
    mx_expand_column: "展开列 subtype",
    mx_collapse_column: "收起列 subtype",
    mx_legend_label: "胜率配色：",
    mx_source_note: "数据来自 Videre 众包对局记录，以官方公开牌表分类；因官方仅公开前32牌表，对局数据并不包含全体参赛者。",
    // Tooltip copy.
    mx_matchup_tip: "矩阵内数值为行套牌对列套牌的对局胜率。大字为胜率，小字为 95% 置信区间半宽（±范围），样本越多区间越窄。悬停或点击查看具体战绩。",
    appr_tip: "该套牌对应瑞士轮理论轮数的平均得分，按总积分除以理论总轮数计算。范围 0–3 分，分数越高代表该套牌整体战绩越好。",
    hs_share_tip: "所选区间内该套牌高分数量占总高分套牌数量的比例。",
    t8_share_tip: "所选区间内该套牌八强数量占总八强数量的比例。",
    conv_tip: "所选区间内该套牌高分牌手中最终进入八强的比例。",
    hs_count_tip: "所选区间内该套牌打出高分成绩的数量。高分定义为瑞士轮积分达到等效于胜率超过 50% 的门槛，门槛随赛事轮数变化（如 6 轮赛事需 12 分以上）。",
    t8_count_tip: "所选区间内该套牌进入赛事前八名的数量。",
    hs_count_tip: "所选区间内该套牌打出高分成绩的数量。高分定义为瑞士轮积分达到等效于胜率超过 50% 的门槛，门槛随赛事轮数变化（如 6 轮赛事需 12 分以上）。",
    t8_count_tip: "所选区间内该套牌进入赛事前八名的数量。",
    // Statistics-tab data-source note.
    stats_source_note: "本页面数据源为 MTGO 官网，官网仅放出各赛事前 32 的牌表，所以数据会有一定误差。",
    stats_source_tip: "整体 meta 占比误差较大，所以本页面不予展示，转而统计高分套牌数量。因为一方面高分套牌更有参考价值（会有更少情况被 0 胜随机套牌污染占比），另一方面高分套牌在前 32 中被囊括的比例也更大（不过超过 80 人左右的赛事中依旧会有高分套牌被 cut 掉）。",
    meta_rules_updated: "套牌类型特征最后更新",
    meta_data_updated: "数据最后更新",
  },
  en: {
    siteTitle: "MTG Meta Analytics",
    range_1w: "1 Week", range_4w: "4 Weeks", range_12w: "12 Weeks", range_36w: "36 Weeks",
    format_standard: "Standard", format_pioneer: "Pioneer", format_modern: "Modern",
    col_archetype: "Archetype", col_appr: "Pts/Round", col_hs_count: "High-Score", col_hs_share: "HS Share",
    col_t8_count: "Top 8", col_t8_share: "T8 Share", col_conv: "Conversion",
    chart_hs: "HS Share", chart_t8: "T8 Share",
    period: "Period", loading: "Loading…",
    best_deck: "Best Deck",
    main_deck: "Main", side_deck: "Sideboard", na: "N/A", others:"Others",
    tab_synthetic: "4-Week Average Build", tab_real: "Representative Deck",
    core_group: "Core", flex_group: "Flex",
    avg_sample: "sample",
    avg_none: "Insufficient 4-week sample, no average deck",
    dev_title: "Deviation", dev_suffix: "",
    dev_desc: "Deviation measures how much this deck differs from the last-4-week average build; higher means more original. It does not indicate strength.",
    diff_fewer: "Fewer than average", diff_more: "More than average",
    typical_qty: "avg",
    change_title: "Recent Build Change", change_suffix: "",
    change_desc: "Measures how much this week's build differs from the prior 4 weeks' average build; higher means a bigger shift this week.",
    change_note_recent: "Insufficient sample this week; no change score",
    change_note_prior: "No historical build data; cannot compute change",
    change_note_nobase: "Insufficient 4-week sample; no change score",
    view_stats: "MTGO Official Stats", view_pickup: "Weekly Pickup",
    pickup_weeks: "Archive", pickup_existing: "New Tech",
    pickup_new: "New Archetypes", pickup_empty: "None this week",
    pickup_no_data: "No weekly pickup content yet",
    pk_rank: "Rank", pk_score: "Score",
    view_matchup: "Matchups",
    mx_overall: "Overall",
    mx_wld: "W-L-D",
    mx_na: "No data / low sample",
    mx_low_sample: "Low sample (interpret with care)",
    mx_expand_all: "Expand all subtypes",
    mx_collapse_all: "Collapse all subtypes",
    mx_expand_row: "Expand row subtypes",
    mx_collapse_row: "Collapse row subtypes",
    mx_expand_column: "Expand column subtypes",
    mx_collapse_column: "Collapse column subtypes",
    mx_legend_label: "Win-rate color:",
    mx_source_note: "Data from Videre crowd-sourced matches, classified by official published decklists. Since MTGO only publishes the Top 32 decklists, the match data does not cover all entrants.",
    mx_matchup_tip: "Row deck's match win rate vs. column deck. Large number is win rate; small number is the 95% confidence interval half-width (±). More samples means a narrower interval. Hover or click for exact record.",
    appr_tip: "Average points over the theoretical number of Swiss rounds, computed as total points divided by total theoretical rounds. Range 0–3; higher means better overall performance.",
    hs_share_tip: "Share of this deck's high-score count out of the total high-score count in the selected range.",
    t8_share_tip: "Share of this deck's Top 8 count out of the total Top 8 count in the selected range.",
    conv_tip: "Share of this deck's high-scoring players who reached Top 8 in the selected range.",
    stats_source_note: "Data on this page comes from the official MTGO site, which only publishes each event's Top 32 decklists, so figures carry some margin of error.",
    stats_source_tip: "Overall metagame-share estimates carry large error, so this page does not display them; instead it counts high-scoring decks. High-scoring decks are more meaningful (their share is less polluted by random 0-win decks), and a larger fraction of them is captured within the Top 32 (though in events with ~80+ players some high-scoring decks are still cut).",
    meta_rules_updated: "Archetype rules last updated",
    meta_data_updated: "Data last updated",
  },
};

// ===================== Page state =====================
let lang = "zh";
let currentFormat = "standard";
let currentRange = 1;
let currentData = null;
let sortKey = "hs_share";
let sortDir = "desc";
let chartInstance = null;
let currentDecks = null;   // decks_Xw.json for the active range.
let openedArch = null;     // Expanded archetype, retained across sorting and range changes.
let avgMode = "synthetic"; // Average-deck tab: synthetic (default) or representative real deck.
let currentView = "stats";       // stats / pickup
let pickupIndex = null;          // pickup/index.json
let currentPickupWeek = null;    // Active Pickup week.
let currentPickupData = null;    // {week}.json for the active Pickup week.
let mxExpandedRows = new Set();   // Independently expanded parent row IDs.
let mxExpandedColumns = new Set();// Independently expanded parent column IDs.

const COLSPAN = 7;         // Number of table columns spanned by an expanded row.

// ===================== Localization lookup =====================
function t(key) {
  if (I18N[lang] && I18N[lang][key] !== undefined) return I18N[lang][key];
  if (I18N.en[key] !== undefined) return I18N.en[key];
  return key;
}
function archetypeName(en) { return en; }   // TODO: Add the localization map.
function cardName(en) { return en; }         // TODO: Add the localization map.

const _cardImgCache = {};
let _previewToken = 0;
function showCardPreview(en, ev) {
  const box = document.getElementById("cardPreview");
  const token = ++_previewToken;
  const place = () => { box.style.display = "block"; moveCardPreview(ev); };
  if (_cardImgCache[en]) { box.src = _cardImgCache[en]; place(); }
  else {
    const pre = new Image();
    pre.onload = () => {
      if (token !== _previewToken) return;
      _cardImgCache[en] = pre.src; box.src = pre.src; place();
    };
    pre.src = cardImageUrl(en);
  }
}
function moveCardPreview(ev) {
  const box = document.getElementById("cardPreview");
  if (box.style.display !== "block") return;
  const w = 240, h = 336, pad = 16;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > window.innerWidth)  x = ev.clientX - w - pad;
  if (y + h > window.innerHeight) y = window.innerHeight - h - pad;
  if (y < pad) y = pad;
  box.style.left = x + "px"; box.style.top = y + "px";
}
function hideCardPreview() {
  _previewToken++;
  document.getElementById("cardPreview").style.display = "none";
}

// ===================== Page-shell rendering =====================
function renderFormatTabs() {
  const box = document.getElementById("formatTabs");
  box.innerHTML = "";
  FORMATS.forEach(f => {
    const b = document.createElement("button");
    b.textContent = t("format_" + f.key);
    b.disabled = !f.enabled;
    if (f.key === currentFormat) b.classList.add("active");
    b.onclick = () => {
      if (f.enabled && currentFormat !== f.key) {
        currentFormat = f.key;
        currentPickupWeek = null;
        mxExpandedRows = new Set();
        mxExpandedColumns = new Set();
        refreshAll();
      }
    };
    box.appendChild(b);
  });
}
// Visible statistics ranges. The 36-week range remains hidden pending separate review.
const RANGES_SHOWN = [1, 4, 12];
function renderRangeButtons() {
  const box = document.getElementById("rangeButtons");
  box.innerHTML = "";
  RANGES_SHOWN.forEach(n => {
    const b = document.createElement("button");
    b.textContent = t("range_" + n + "w");
    if (n === currentRange) b.classList.add("active");
    b.onclick = () => { currentRange = n; refreshAll(); };
    box.appendChild(b);
  });
}
function renderStaticTexts() {
  document.getElementById("siteTitle").textContent = t("siteTitle");
  document.title = t("siteTitle");
  document.documentElement.lang = (lang === "zh") ? "zh" : "en";
  document.getElementById("langZh").classList.toggle("active", lang === "zh");
  document.getElementById("langEn").classList.toggle("active", lang === "en");
  document.getElementById("statsNote").innerHTML =
    t("stats_source_note") + " " + t("stats_source_tip");
}
function renderMetaLine() {
  const el = document.getElementById("statsMeta");
  if (!el) return;
  if (!metaInfo) { el.textContent = ""; return; }
  const fmtDate = (iso) => {
    if (!iso) return t("na");
    // Keep only the YYYY-MM-DD date component.
    return String(iso).slice(0, 10);
  };
  const parts = [];
  if (metaInfo.rules_updated)
    parts.push(`${t("meta_rules_updated")}: ${fmtDate(metaInfo.rules_updated)}`);
  if (metaInfo.data_updated)
    parts.push(`${t("meta_data_updated")}: ${fmtDate(metaInfo.data_updated)}`);
  el.textContent = parts.join("　|　");
}

// ===================== Data loading =====================
let metaInfo = null;
async function loadMeta() {
  const url = `stats/${currentFormat}/mtgo/meta.json?v=${Date.now()}`;
  try {
    const resp = await fetch(url);
    metaInfo = resp.ok ? await resp.json() : null;
  } catch (e) { metaInfo = null; }
  renderMetaLine();
}

async function loadData() {
  const url = `stats/${currentFormat}/mtgo/range_${currentRange}w.json?v=${Date.now()}`;
  const tp = document.getElementById("tablePlaceholder");
  if (tp) tp.textContent = t("loading");
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    currentData = await resp.json();
    const deckUrl = `stats/${currentFormat}/mtgo/decks_${currentRange}w.json?v=${Date.now()}`;
    try {
      const dResp = await fetch(deckUrl);
      currentDecks = dResp.ok ? await dResp.json() : null;
    } catch (e) { currentDecks = null; }
  } catch (e) {
    currentData = null;
    document.getElementById("tablePanel").innerHTML =
      `<div class="placeholder">加载失败: ${url}<br>${e.message}</div>`;
    return;
  }
  updatePeriodInfo();
  renderTable();
  renderChart();
}
function updatePeriodInfo() {
  if (!currentData) return;
  const p = currentData.period;
  document.getElementById("periodInfo").textContent =
    `${t("period")}: ${p.start} ~ ${p.end}　|　` +
    `${currentData.total_decks} decks　|　HS ${currentData.total_high_score}　|　T8 ${currentData.total_top8}`;
}

// ===================== Statistics table rendering =====================

function sortedArchetypes() {
  const arr = [...currentData.archetypes];
  const keymap = {
    archetype: a => archetypeName(a.name).toLowerCase(),
    appr: a => (a.avg_points_per_round ?? -1),
    hs_count: a => a.high_score_count,
    hs_share: a => a.high_score_share ?? 0,
    t8_count: a => a.top8_count,
    t8_share: a => a.top8_share ?? 0,
    conv: a => (a.conversion ?? -1),
  };
  const f = keymap[sortKey] || keymap.hs_share;
  arr.sort((x, y) => {
    const vx = f(x), vy = f(y);
    if (vx < vy) return sortDir === "asc" ? -1 : 1;
    if (vx > vy) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
  return arr;
}
function renderTable() {
  if (!currentData) return;
  const cols = [
    { key: "archetype", label: "col_archetype", align: "left" },
    { key: "appr",      label: "col_appr",      align: "right" },
    { key: "hs_count",  label: "col_hs_count",  align: "right" },
    { key: "hs_share",  label: "col_hs_share",  align: "right" },
    { key: "t8_count",  label: "col_t8_count",  align: "right" },
    { key: "t8_share",  label: "col_t8_share",  align: "right" },
    { key: "conv",      label: "col_conv",      align: "right" },
  ];
  // Map columns to tooltip keys only when explanatory copy exists.
  const colTips = {
    hs_count: "hs_count", hs_share: "hs_share",
    t8_count: "t8_count", t8_share: "t8_share",
    appr: "appr", conv: "conv",
  };
  let html = '<table class="data-table"><thead><tr>';
  cols.forEach(c => {
    let arrow = "";
    if (c.key === sortKey) arrow = sortDir === "desc" ? " ▼" : " ▲";
    const tip = colTips[c.key] ? tipIconHtml(colTips[c.key]) : "";
    html += `<th style="text-align:${c.align}" data-key="${c.key}" class="sortable">${t(c.label)}${arrow}${tip}</th>`;
  });
  html += "</tr></thead><tbody>";
  sortedArchetypes().filter(a => a.high_score_count > 0).forEach(a => {
    html += "<tr>"
      + `<td><a href="#" class="arch-link" data-name="${encodeURIComponent(a.name)}">${archetypeName(a.name)}</a></td>`
      + `<td style="text-align:right">${fmtAppr(a.avg_points_per_round)}</td>`
      + `<td style="text-align:right">${a.high_score_count}</td>`
      + `<td style="text-align:right">${fmtPct(a.high_score_share)}</td>`
      + `<td style="text-align:right">${a.top8_count}</td>`
      + `<td style="text-align:right">${fmtPct(a.top8_share)}</td>`
      + `<td style="text-align:right">${fmtPct(a.conversion)}</td>`
      + "</tr>";
  });
  html += "</tbody></table>";

  const panel = document.getElementById("tablePanel");
  panel.innerHTML = html;

  panel.querySelectorAll("th.sortable").forEach(th => {
    th.onclick = (ev) => {
      // Clicking a tooltip icon or overlay must not trigger sorting.
      if (ev.target.closest(".tip-wrap")) return;
      const k = th.dataset.key;
      if (sortKey === k) { sortDir = (sortDir === "desc") ? "asc" : "desc"; }
      else { sortKey = k; sortDir = "desc"; }
      renderTable();
    };
  });
  panel.querySelectorAll("a.arch-link").forEach(link => {
    link.onclick = (ev) => {
      ev.preventDefault();
      const name = decodeURIComponent(link.dataset.name);
      toggleDeckRow(name, link.closest("tr"));
    };
  });
  panel.onmouseover = (ev) => {
    const link = ev.target.closest("a.card-link");
    if (link) showCardPreview(decodeURIComponent(link.dataset.card), ev);
  };
  panel.onmousemove = (ev) => {
    if (document.getElementById("cardPreview").style.display === "block") moveCardPreview(ev);
  };
  panel.onmouseout = (ev) => {
    const link = ev.target.closest("a.card-link");
    if (link) hideCardPreview();
  };

  if (openedArch) {
    const arch = openedArch;
    openedArch = null;
    const link = panel.querySelector(`a.arch-link[data-name="${encodeURIComponent(arch)}"]`);
    if (link) toggleDeckRow(arch, link.closest("tr"));
  }
}

// ===================== Bar-chart rendering =====================
function renderChart(){
  if(!currentData) return;
  let arr=[...currentData.archetypes].sort((a,b)=>(b.high_score_share??0)-(a.high_score_share??0));
  let shown=arr.filter(a=>(a.high_score_share??0)>=CHART_MIN_SHARE);
  let rest =arr.filter(a=>(a.high_score_share??0)< CHART_MIN_SHARE);
  const labels=shown.map(a=>archetypeName(a.name));
  const hsData=shown.map(a=>+((a.high_score_share??0)*100).toFixed(1));
  const t8Data=shown.map(a=>+((a.top8_share??0)*100).toFixed(1));
  if(rest.length>0){
    const othHs=rest.reduce((s,a)=>s+(a.high_score_share??0),0);
    const othT8=rest.reduce((s,a)=>s+(a.top8_share??0),0);
    labels.push(t("others"));
    hsData.push(+(othHs*100).toFixed(1));
    t8Data.push(+(othT8*100).toFixed(1));
  }
  const canvas=document.getElementById("metaChart");
  canvas.parentElement.style.height=Math.max(200, labels.length*34+60)+"px";
  if(chartInstance) chartInstance.destroy();
  chartInstance=new Chart(canvas,{type:"bar",data:{labels,datasets:[
    {label:t("chart_hs"),data:hsData,backgroundColor:"#9cc0e0"},
    {label:t("chart_t8"),data:t8Data,backgroundColor:"#3b6ea5"}
  ]},options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,
    scales:{x:{beginAtZero:true,ticks:{callback:v=>v+"%"}}},
    plugins:{legend:{position:"top"},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+": "+ctx.parsed.x+"%"}}}}});
}

// ===================== Inline deck details =====================

function deckCardList(cards) {
  if (!cards || cards.length === 0) return "<div class='placeholder'>—</div>";
  const total = cards.reduce((s, c) => s + (c.qty || 0), 0);
  let html = `<div class="deck-total">${total}</div><ul class="card-list">`;
  cards.forEach(c => {
    const dataCard = encodeURIComponent(c.name).replace(/"/g, "&quot;");
    html += `<li><span class="qty">${c.qty}</span>`
      + `<a class="card-link" href="${cardUrl(c.name)}" target="_blank" rel="noopener" data-card="${dataCard}">${cardName(c.name)}</a></li>`;
  });
  html += `</ul>`;
  return html;
}
function deckMetaLine(rec) {
  if (!rec) return "";
  const player = rec.player || "-";
  const fr = (rec.final_rank === null || rec.final_rank === undefined || rec.final_rank === "") ? "-" : rec.final_rank;
  const sc = (rec.swiss_score === null || rec.swiss_score === undefined || rec.swiss_score === "") ? "-" : rec.swiss_score;
  const dt = rec.starttime ? rec.starttime.slice(0, 10) : "-";
  return `<div class="deck-meta">${player} · rank ${fr} · score ${sc} · ${dt}</div>`;
}
function deckMainSideHtml(rec) {
  return `<h4>${t("main_deck")}</h4>${deckCardList(getMain(rec))}`
       + `<h4>${t("side_deck")}</h4>${deckCardList(getSide(rec))}`;
}

// Single-deck construction deviation and difference breakdown.
function deviationHtml(best) {
  if (!best || best.deviation === null || best.deviation === undefined) return "";
  const p = best.deviation;
  let html = `<div class="dev-box">`
    + `<span style="color:#666">${t("dev_title")}: </span>`
    + `<span class="dev-score">${p}${t("dev_suffix")}</span>`
    + `<div class="dev-note">${t("dev_desc")}</div>`;
  const diff = best.deviation_diff;
  if (diff) {
    const fewer = filterDiff(diff.fewer);
    const more  = filterDiff(diff.more);
    if (fewer.length || more.length) {
      html += `<div class="diff-cols">`;
      html += `<div class="diff-col fewer"><h5>${t("diff_fewer")}</h5>${diffListHtml(fewer)}</div>`;
      html += `<div class="diff-col more"><h5>${t("diff_more")}</h5>${diffListHtml(more)}</div>`;
      html += `</div>`;
    }
  }
  html += `</div>`;
  return html;
}
function filterDiff(items) {
  if (!items) return [];
  return items.filter(it => {
    const dq = Number(it.deck_qty) || 0;
    const tq = Number(it.typical_qty) || 0;
    return Math.abs(dq - tq) >= DIFF_MIN;
  });
}
function diffListHtml(items) {
  if (!items || items.length === 0) return "<div class='placeholder' style='padding:4px 0'>—</div>";
  let html = `<ul class="diff-list">`;
  items.forEach(it => {
    const dataCard = encodeURIComponent(it.name).replace(/"/g, "&quot;");
    const dq = it.deck_qty;
    const tq = (it.typical_qty === null || it.typical_qty === undefined) ? "-" : it.typical_qty;
    html += `<li>`
      + `<a class="card-link" href="${cardUrl(it.name)}" target="_blank" rel="noopener" data-card="${dataCard}">${cardName(it.name)}</a> `
      + `<span class="diff-qty">${dq} (${t("typical_qty")} ${tq})</span></li>`;
  });
  html += `</ul>`;
  return html;
}

// Recent construction change.
function recentChangeHtml(avg) {
  const val = avg ? avg.recent_change : null;
  const reason = avg ? avg.recent_change_reason : null;
  if (val === null || val === undefined) {
    let msg = "";
    if (reason === "prior") msg = t("change_note_prior");
    else if (reason === "recent") msg = t("change_note_recent");
    else if (reason === "nobase") msg = t("change_note_nobase");
    if (!msg) return "";
    return `<div class="change-box"><span style="color:#666">${t("change_title")}: </span>`
      + `<span class="change-note">${msg}</span></div>`;
  }
  return `<div class="change-box">`
    + `<span style="color:#666">${t("change_title")}: </span>`
    + `<span class="change-score">${val}${t("change_suffix")}</span>`
    + `<div class="change-note">${t("change_desc")}</div></div>`;
}

// Core / Flex groups for the synthetic average deck.
function coreFlexHtml(avg) {
  const core = (avg && avg.core) || [];
  const flex = (avg && avg.flex) || [];
  if (core.length === 0 && flex.length === 0) {
    return `<div class="placeholder">${t("avg_none")}</div>`;
  }
  const groupHtml = (items, cls, label) => {
    if (!items.length) return "";
    let h = `<div class="cf-group ${cls}"><h4>${label}</h4><ul class="cf-list">`;
    items.forEach(c => {
      const dataCard = encodeURIComponent(c.name).replace(/"/g, "&quot;");
      h += `<li><span class="qty">${c.mean_qty}</span>`
        + `<a class="card-link" href="${cardUrl(c.name)}" target="_blank" rel="noopener" data-card="${dataCard}">${cardName(c.name)}</a></li>`;
    });
    h += `</ul></div>`;
    return h;
  };
  return groupHtml(core, "cf-core", t("core_group"))
       + groupHtml(flex, "cf-flex", t("flex_group"));
}

// Average-deck section with two tabs and recent-change context.
function averageDeckHtml(entry) {
  const avg = entry ? entry.average_deck : null;
  if (!avg || (avg.sample_size === 0 && !(avg.core && avg.core.length))) {
    return recentChangeHtml(avg) + `<div class="placeholder">${t("avg_none")}</div>`;
  }
  const ss = (avg.sample_size ?? "-");
  // Tab controls.
  let html = `<div class="avg-toggle">`
    + `<button data-mode="synthetic" class="${avgMode==='synthetic'?'active':''}">${t("tab_synthetic")}</button>`
    + `<button data-mode="real" class="${avgMode==='real'?'active':''}">${t("tab_real")}</button>`
    + `<span style="align-self:center;color:#aaa;font-size:11px">(${t("avg_sample")} ${ss})</span>`
    + `</div>`;
  // Keep recent-change context between the tabs and deck content.
  html += recentChangeHtml(avg);
  // Deck content changes with the selected tab.
  if (avgMode === "real") {
    html += avg.medoid ? (deckMetaLine(avg.medoid) + deckMainSideHtml(avg.medoid))
                       : `<div class="placeholder">—</div>`;
  } else {
    html += coreFlexHtml(avg);
  }
  return html;
}


// Rebind average-deck tabs whenever the detail panel is redrawn.
function bindAvgToggle(tr, archName) {
  tr.querySelectorAll(".avg-toggle button").forEach(b => {
    b.onclick = () => {
      avgMode = b.dataset.mode;
      const col = tr.querySelector(".deck-columns .deck-col:last-child");
      const entry = currentDecks && currentDecks.decks ? currentDecks.decks[archName] : null;
      if (col) col.innerHTML = averageDeckHtml(entry);
      bindAvgToggle(tr, archName);
    };
  });
}

function deckBoxHtml(archName) {
  const entry = currentDecks && currentDecks.decks ? currentDecks.decks[archName] : null;
  const best = entry ? entry.best_deck : null;
  let inner = `<button class="deck-close" onclick="closeDeckRow()">✕</button>`
    + `<div class="deck-title">${archetypeName(archName)}</div>`;
  if (!entry) {
    inner += `<div class="placeholder">—</div>`;
    return `<div class="deck-box">${inner}</div>`;
  }
  let leftCol = `<div class="deck-col"><h3>${t("best_deck")}</h3>`;
  if (best) {
    leftCol += deckMetaLine(best);
    leftCol += deviationHtml(best);
    leftCol += deckMainSideHtml(best);
  } else {
    leftCol += `<div class="placeholder">—</div>`;
  }
  leftCol += `</div>`;
  const rightCol = `<div class="deck-col">${averageDeckHtml(entry)}</div>`;
  inner += `<div class="deck-columns">${leftCol}${rightCol}</div>`;
  return `<div class="deck-box">${inner}</div>`;
}

function toggleDeckRow(archName, rowEl) {
  const next = rowEl.nextElementSibling;
  const alreadyOpen = next && next.classList.contains("deck-row")
                      && next.dataset.arch === archName;
  closeDeckRow();
  if (alreadyOpen) { openedArch = null; return; }
  openedArch = archName;
  const tr = document.createElement("tr");
  tr.className = "deck-row";
  tr.dataset.arch = archName;
  tr.innerHTML = `<td colspan="${COLSPAN}">${deckBoxHtml(archName)}</td>`;
  rowEl.parentNode.insertBefore(tr, rowEl.nextSibling);
  bindAvgToggle(tr, archName);
}

function closeDeckRow() {
  hideCardPreview();
  document.querySelectorAll("tr.deck-row").forEach(r => r.remove());
  openedArch = null;
}
// ===================== Product-view switch =====================
function renderViewSwitch() {
  const box = document.getElementById("viewSwitch");
  box.innerHTML = "";
  [["stats", "view_stats"], ["matchup", "view_matchup"], ["pickup", "view_pickup"]].forEach(([key, label]) => {
    const b = document.createElement("button");
    b.textContent = t(label);
    if (key === currentView) b.classList.add("active");
    b.onclick = () => { currentView = key; refreshAll(); };
    box.appendChild(b);
  });
}
function applyView() {
  document.getElementById("statsView").style.display = (currentView === "stats") ? "" : "none";
  document.getElementById("pickupView").style.display = (currentView === "pickup") ? "" : "none";
  document.getElementById("matchupView").style.display = (currentView === "matchup") ? "" : "none";
}

// ===================== Weekly Pickup data and rendering =====================
async function loadPickup() {
  const idxUrl = `stats/${currentFormat}/mtgo/pickup/index.json?v=${Date.now()}`;
  try {
    const resp = await fetch(idxUrl);
    pickupIndex = resp.ok ? await resp.json() : null;
  } catch (e) { pickupIndex = null; }

  const weeks = (pickupIndex && pickupIndex.weeks) || [];
  if (!weeks.length) {
    document.getElementById("pickupWeeks").innerHTML =
      `<h3>${t("pickup_weeks")}</h3>`;
    document.getElementById("pickupContent").innerHTML =
      `<div class="pickup-empty">${t("pickup_no_data")}</div>`;
    return;
  }
  // Weeks are descending, so select the latest by default.
  if (!currentPickupWeek || !weeks.some(w => w.week === currentPickupWeek)) {
    currentPickupWeek = weeks[0].week;
  }
  renderPickupWeeks(weeks);
  await loadPickupWeek(currentPickupWeek);
}
function renderPickupWeeks(weeks) {
  let html = `<h3>${t("pickup_weeks")}</h3>`;
  weeks.forEach(w => {
    const active = (w.week === currentPickupWeek) ? " active" : "";
    html += `<button class="wk-btn${active}" data-week="${w.week}">${w.week}`
      + `<span class="wk-sub">${w.start} ~ ${w.end}</span></button>`;
  });
  const box = document.getElementById("pickupWeeks");
  box.innerHTML = html;
  box.querySelectorAll(".wk-btn").forEach(btn => {
    btn.onclick = async () => {
      currentPickupWeek = btn.dataset.week;
      renderPickupWeeks(weeks);
      await loadPickupWeek(currentPickupWeek);
    };
  });
}
async function loadPickupWeek(week) {
  const url = `stats/${currentFormat}/mtgo/pickup/${week}.json?v=${Date.now()}`;
  const content = document.getElementById("pickupContent");
  content.innerHTML = `<div class="pickup-empty">${t("loading")}</div>`;
  try {
    const resp = await fetch(url);
    currentPickupData = resp.ok ? await resp.json() : null;
  } catch (e) { currentPickupData = null; }
  renderPickupContent();
}
function renderPickupContent() {
  const content = document.getElementById("pickupContent");
  if (!currentPickupData) {
    content.innerHTML = `<div class="pickup-empty">${t("pickup_empty")}</div>`;
    return;
  }
  const existing = currentPickupData.existing_changes || [];
  const newArch = currentPickupData.new_archetypes || [];
  let html = "";
  html += pickupGroupHtml(t("pickup_existing"), existing);
  html += pickupGroupHtml(t("pickup_new"), newArch);
  content.innerHTML = html;

  // Expand/collapse behavior and card-image hover previews.
  content.querySelectorAll(".pk-head").forEach(head => {
    head.onclick = () => head.closest(".pk-card").classList.toggle("open");
  });
  content.onmouseover = (ev) => {
    const link = ev.target.closest("a.card-link");
    if (link) showCardPreview(decodeURIComponent(link.dataset.card), ev);
  };
  content.onmousemove = (ev) => {
    if (document.getElementById("cardPreview").style.display === "block") moveCardPreview(ev);
  };
  content.onmouseout = (ev) => {
    if (ev.target.closest("a.card-link")) hideCardPreview();
  };
}
function pickupGroupHtml(title, items) {
  let html = `<div class="pickup-group"><h2>${title}</h2>`;
  if (!items.length) {
    html += `<div class="pickup-empty">${t("pickup_empty")}</div></div>`;
    return html;
  }
  items.forEach((it, i) => { html += pickupCardHtml(it, i); });
  html += `</div>`;
  return html;
}
function pickupCardHtml(it, idx) {
  const dev = (it.deviation === null || it.deviation === undefined)
    ? "" : `<span class="pk-dev">${t("dev_title")} ${it.deviation}${t("dev_suffix")}</span>`;
  const fr = (it.final_rank === null || it.final_rank === undefined) ? "-" : it.final_rank;
  const sc = (it.swiss_score === null || it.swiss_score === undefined) ? "-" : it.swiss_score;
  const dt = it.starttime ? it.starttime.slice(0, 10) : "";
  const brief = `${it.player || "-"} · ${t("pk_rank")} ${fr} · ${t("pk_score")} ${sc}${dt ? " · " + dt : ""}`;
  const comment = (lang === "en" && it.comment_en) ? it.comment_en : (it.comment_zh || "");

  let body = "";
  if (comment) body += `<div class="pk-comment">${escapeHtml(comment)}</div>`;
  body += `<div class="pk-decks">`
    + `<div class="deck-col"><h4>${t("main_deck")}</h4>${deckCardList(it.main_deck || [])}</div>`
    + `<div class="deck-col"><h4>${t("side_deck")}</h4>${deckCardList(it.side_deck || [])}</div>`
    + `</div>`;

  return `<div class="pk-card">`
    + `<div class="pk-head"><div>`
    + `<div class="pk-name">${archetypeName(it.archetype)}</div>`
    + `<div class="pk-brief">${brief}</div></div>`
    + dev + `</div>`
    + `<div class="pk-body">${body}</div>`
    + `</div>`;
}


// ===================== Language and refresh =====================
function setLang(l) {
  lang = l;
  refreshAll();
}

function refreshAll() {
  renderStaticTexts();
  renderViewSwitch();
  renderFormatTabs();
  applyView();
  if (currentView === "stats") {
    renderRangeButtons();
    loadData();
    loadMeta();
  } else if (currentView === "pickup") {
    loadPickup();
  } else if (currentView === "matchup") {
    loadMatchup();
  }
}

// ===================== Matchup matrix =====================
const MX_RANGES = [1, 4, 12];   // Keep 1/4/12 visible; 36 weeks requires separate review.
let mxRange = 4;                // Default to four weeks.
let mxData = null;

// Map win rate to a linear red (0%), yellow (50%), and green (100%) scale.
function mxColor(wr) {
  if (wr === null || wr === undefined) return null;
  const p = Math.max(0, Math.min(1, wr));
  // 0 -> red (192,57,43), 0.5 -> yellow (232,200,74), 1 -> green (39,136,74).
  let r, g, b;
  if (p < 0.5) {
    const k = p / 0.5;
    r = 192 + (232 - 192) * k; g = 57 + (200 - 57) * k; b = 43 + (74 - 43) * k;
  } else {
    const k = (p - 0.5) / 0.5;
    r = 232 + (39 - 232) * k; g = 200 + (136 - 200) * k; b = 74 + (74 - 74) * k;
  }
  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
}
function mxTextColor(wr) {
  // Use dark text on yellow and white text on darker red or green.
  if (wr === null || wr === undefined) return "#b0b4b8";
  return (wr >= 0.40 && wr <= 0.60) ? "#333" : "#fff";
}

function renderMxRangeButtons() {
  const box = document.getElementById("mxRangeButtons");
  box.innerHTML = "";
  MX_RANGES.forEach(n => {
    const b = document.createElement("button");
    b.textContent = t("range_" + n + "w");
    if (n === mxRange) b.classList.add("active");
    b.onclick = () => { mxRange = n; loadMatchup(); };
    box.appendChild(b);
  });
}

function renderMxLegend() {
  document.getElementById("mxNote").innerHTML =
    t("mx_source_note") + " " + t("mx_matchup_tip");
  document.getElementById("mxLegend").innerHTML =
    `<span>${t("mx_legend_label")}</span>`
    + `<div><div class="bar"></div><div class="ends"><span>0%</span><span>50%</span><span>100%</span></div></div>`
    + `<span><span class="na-chip"></span>${t("mx_na")}</span>`
    + `<span style="color:#999"><span style="display:inline-block;width:0;height:0;border-top:7px solid rgba(0,0,0,0.4);border-left:7px solid transparent;vertical-align:middle;margin-right:4px"></span>${t("mx_low_sample")}</span>`;
}

function renderMxExpandControls(view) {
  const box = document.getElementById("mxExpandControls");
  const eligible = view ? view.expandableParentIds : [];
  if (!eligible.length) {
    box.innerHTML = "";
    return;
  }
  const allExpanded = eligible.every(parentId =>
    mxExpandedRows.has(parentId) && mxExpandedColumns.has(parentId)
  );
  const button = document.createElement("button");
  button.className = "mx-expand-all";
  button.textContent = t(allExpanded ? "mx_collapse_all" : "mx_expand_all");
  button.setAttribute("aria-pressed", allExpanded ? "true" : "false");
  button.onclick = () => {
    if (allExpanded) {
      mxExpandedRows = new Set();
      mxExpandedColumns = new Set();
    } else {
      mxExpandedRows = new Set(eligible);
      mxExpandedColumns = new Set(eligible);
    }
    renderMatrix();
  };
  box.replaceChildren(button);
}

function mxAxisButton(node, axis, expanded) {
  if (!node.expandable) return "";
  const action = expanded
    ? (axis === "row" ? "mx_collapse_row" : "mx_collapse_column")
    : (axis === "row" ? "mx_expand_row" : "mx_expand_column");
  const symbol = expanded ? "−" : "+";
  return `<button class="mx-axis-toggle mx-${axis}-toggle"`
    + ` data-axis="${axis}" data-parent="${node.parentId}"`
    + ` aria-expanded="${expanded ? "true" : "false"}"`
    + ` aria-label="${escapeHtml(t(action))}: ${escapeHtml(node.name)}"`
    + ` title="${escapeHtml(t(action))}">${symbol}</button>`;
}

async function loadMatchup() {
  renderMxRangeButtons();
  renderMxLegend();
  const url = `stats/${currentFormat}/mtgo/matchup_${mxRange}w.json?v=${Date.now()}`;
  const holder = document.getElementById("mxTable");
  holder.innerHTML = `<div class="placeholder">${t("loading")}</div>`;
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    mxData = await resp.json();
  } catch (e) {
    mxData = null;
    holder.innerHTML = `<div class="placeholder">${t("loading")} ✕<br>${e.message}</div>`;
    return;
  }
  renderMatrix();
}

function mxCellHtml(cell, isOverall) {
  const cls = "cell" + (isOverall ? " overall" : "")
    + (cell && cell.low_sample ? " mx-cell-low" : "");
  if (!cell || cell.win_rate === null || cell.win_rate === undefined || cell.matches === 0) {
    return `<td class="${cls} na" data-empty="1">–</td>`;
  }
  const wr = cell.win_rate;
  const bg = mxColor(wr);
  const fg = mxTextColor(wr);
  const wrTxt = (wr * 100).toFixed(1);
  const ciTxt = (cell.ci_half !== null && cell.ci_half !== undefined)
    ? "±" + (cell.ci_half * 100).toFixed(1) : "";
  const payload = encodeURIComponent(JSON.stringify(
    { w: cell.wins, l: cell.losses, d: cell.draws, m: cell.matches }));
  return `<td class="${cls}" style="background:${bg};color:${fg}" data-mx="${payload}">`
    + `<div class="mx-wr">${wrTxt}</div>`
    + (ciTxt ? `<div class="mx-ci">${ciTxt}</div>` : "")
    + `</td>`;
}

function renderMatrix() {
  if (!mxData) return;
  let view;
  try {
    view = MtgMatchup.buildView(
      mxData,
      Array.from(mxExpandedRows),
      Array.from(mxExpandedColumns)
    );
  } catch (e) {
    document.getElementById("mxTable").innerHTML =
      `<div class="placeholder">${escapeHtml(e.message)}</div>`;
    document.getElementById("mxExpandControls").innerHTML = "";
    return;
  }
  renderMxExpandControls(view);

  let html = `<table class="mx-table"><thead><tr><th class="corner"></th>`;
  // The first data column is Overall.
  html += `<th class="col-head overall-head"><div>${t("mx_overall")}</div></th>`;
  view.columns.forEach(node => {
    const subtypeClass = node.kind === "subtype" ? " subtype-head" : "";
    const expanded = mxExpandedColumns.has(node.parentId);
    html += `<th class="col-head${subtypeClass}"><div title="${escapeHtml(node.parentName)}">`
      + mxAxisButton(node, "column", expanded)
      + `<span>${escapeHtml(archetypeName(node.name))}</span></div></th>`;
  });
  html += `</tr></thead><tbody>`;

  view.rows.forEach(node => {
    const subtypeClass = node.kind === "subtype" ? " subtype-row" : "";
    const expanded = mxExpandedRows.has(node.parentId);
    html += `<tr><th class="row-head${subtypeClass}" title="${escapeHtml(node.parentName)}">`
      + mxAxisButton(node, "row", expanded)
      + `<span>${escapeHtml(archetypeName(node.name))}</span></th>`;
    // Overall column.
    html += mxCellHtml(view.overall[node.id], true);
    // Opponent columns.
    view.columns.forEach(column => {
      html += mxCellHtml(view.matrix[node.id][column.id], false);
    });
    html += `</tr>`;
  });
  html += `</tbody></table>`;

  const holder = document.getElementById("mxTable");
  holder.innerHTML = html;

  // Show the win-draw-loss overlay on hover or click.
  const pop = document.getElementById("mxHoverPop");
  holder.onmousemove = (ev) => {
    const td = ev.target.closest("td.cell");
    if (!td || td.dataset.empty) { pop.style.display = "none"; return; }
    try {
      const o = JSON.parse(decodeURIComponent(td.dataset.mx));
      pop.textContent = `${t("mx_wld")}: ${o.w}-${o.l}-${o.d} (${o.m})`;
      pop.style.display = "block";
      pop.style.left = (ev.clientX + 14) + "px";
      pop.style.top = (ev.clientY + 14) + "px";
    } catch (e) { pop.style.display = "none"; }
  };
  holder.onmouseleave = () => { pop.style.display = "none"; };
  // Touch/click toggles the same overlay; clicking elsewhere hides it.
  holder.onclick = (ev) => {
    const toggle = ev.target.closest(".mx-axis-toggle");
    if (toggle) {
      const target = toggle.dataset.axis === "row"
        ? mxExpandedRows : mxExpandedColumns;
      if (target.has(toggle.dataset.parent)) target.delete(toggle.dataset.parent);
      else target.add(toggle.dataset.parent);
      renderMatrix();
      return;
    }
    const td = ev.target.closest("td.cell");
    if (!td || td.dataset.empty) return;
    try {
      const o = JSON.parse(decodeURIComponent(td.dataset.mx));
      pop.textContent = `${t("mx_wld")}: ${o.w}-${o.l}-${o.d} (${o.m})`;
      pop.style.display = "block";
      const r = td.getBoundingClientRect();
      pop.style.left = (r.left + 6) + "px";
      pop.style.top = (r.bottom + 4) + "px";
    } catch (e) {}
  };
}

// ===================== Shared hover/click tooltip component =====================
// Insert tipIconHtml("i18n-key"); the corresponding copy uses <key>_tip.
function tipIconHtml(termKey) {
  const tipKey = termKey + "_tip";
  const text = t(tipKey);
  const payload = encodeURIComponent(text);
  return `<span class="tip-wrap"><i class="tip-icon" data-tip="${payload}">i</i>`
    + `<span class="tip-pop">${text}</span></span>`;
}
// Global delegation: hover opens, click toggles, and outside click closes.
document.addEventListener("mouseover", (ev) => {
  const wrap = ev.target.closest(".tip-wrap");
  document.querySelectorAll(".tip-wrap.tip-hover").forEach(w => {
    if (w !== wrap) w.classList.remove("tip-hover");
  });
  if (wrap) wrap.classList.add("tip-open", "tip-hover");
});
document.addEventListener("mouseout", (ev) => {
  const wrap = ev.target.closest(".tip-wrap");
  if (wrap && wrap.classList.contains("tip-hover")) {
    wrap.classList.remove("tip-open", "tip-hover");
  }
});
document.addEventListener("click", (ev) => {
  const icon = ev.target.closest(".tip-icon");
  if (icon) {
    const wrap = icon.closest(".tip-wrap");
    wrap.classList.toggle("tip-open");
    ev.stopPropagation();
    return;
  }
  // Close click-opened overlays when clicking elsewhere.
  document.querySelectorAll(".tip-wrap.tip-open").forEach(w => {
    if (!w.classList.contains("tip-hover")) w.classList.remove("tip-open");
  });
});

// Initialize after every function definition.

refreshAll();
