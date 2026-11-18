// Validate observed DOM against the fixed copy, using the site's card resolver.
const cardToken = /\[\[card:([^\[\]|\r\n]+)(?:\|([^\[\]|\r\n]+))?\]\]/g;

function checkCopy(items, language, resolve, observed) {
  const errors = [];
  if (observed.length !== items.length) errors.push('Body paragraph count differs');
  items.forEach((item, index) => {
    const text = item.text[language];
    const actual = observed[index];
    if (!actual) return;
    if (/\[deck:[0-9a-f]{20}\]/.test(text)) errors.push(`Paragraph ${index + 1}: bracketed deck token`);
    const expectedCards = [...text.matchAll(cardToken)].map(match => {
      const card = resolve(match[1]);
      return { text: match[2] || card.displayName, href: card.linkUrl };
    });
    if (JSON.stringify(expectedCards) !== JSON.stringify(actual.cards.map(({text, href}) => ({text, href})))) {
      errors.push(`Paragraph ${index + 1}: missing or incorrect card links`);
    }
    const deckLinks = new Map((item.deck_links || []).map(link => [link.token, link]));
    const expectedDecks = [...text.matchAll(/deck:[0-9a-f]{20}/g)].map(match => {
      const link = deckLinks.get(match[0]);
      const marker = language === 'zh' ? '牌表' : 'decklist';
      return { token: link?.decklist_url || match[0],
        text: text.slice(0, match.index).endsWith(marker) ? marker : link?.label[language] };
    });
    if (JSON.stringify(expectedDecks) !== JSON.stringify(actual.decks.map(({token, text}) => ({token, text})))) {
      errors.push(`Paragraph ${index + 1}: missing or incorrect deck links`);
    }
    if (actual.decks.some(link => /\[$/.test(link.before || '') && /^\]/.test(link.after || ''))) {
      errors.push(`Paragraph ${index + 1}: visible brackets around deck link`);
    }
    if (/\[\[card:|deck:[0-9a-f]{20}/.test(actual.text)) errors.push(`Paragraph ${index + 1}: exposed authoring token`);
  });
  return errors;
}

module.exports = { checkCopy };
