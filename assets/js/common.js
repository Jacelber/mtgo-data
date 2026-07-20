// Shared browser helpers for static product pages.
// Keep product state and MTGO rendering behavior in mtgo.js.

function cardUrl(en) {
  return "https://scryfall.com/search?q=" + encodeURIComponent(`!"${en}"`);
}

// ===================== Card-image hover preview =====================
function cardImageUrl(en) {
  return "https://api.scryfall.com/cards/named?exact="
    + encodeURIComponent(en) + "&format=image&version=normal";
}

function fmtPct(x) {
  if (x === null || x === undefined) return t("na");
  return (x * 100).toFixed(1) + "%";
}
function fmtAppr(x) {
  if (x === null || x === undefined) return t("na");
  return Number(x).toFixed(2);
}

function getMain(rec) { return (rec && (rec.main_deck || rec.mainboard)) || []; }
function getSide(rec) { return (rec && (rec.side_deck || rec.sideboard)) || []; }

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
