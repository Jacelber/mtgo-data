const test = require('node:test');
const assert = require('node:assert/strict');
const { checkCopy } = require('../../tools/landing_copy_check.cjs');
const token = 'deck:' + 'a'.repeat(20);
const item = {text: {zh: `[[card:Dispatch|迅速了结]]：${token}`},
  deck_links: [{token, label: {zh: '某牌手'}}]};
const resolve = () => ({displayName: '迅速了结', linkUrl: 'https://mtgch.com/card/NPH/5/'});
const paragraph = {text: '迅速了结：某牌手',
  cards: [{text: '迅速了结', href: 'https://mtgch.com/card/NPH/5/'}],
  decks: [{token, text: '某牌手', before: '：', after: ''}]};

test('body links require the correct card target and no visible deck wrapper', () => {
  assert.deepEqual(checkCopy([item], 'zh', resolve, [paragraph]), []);
  assert.deepEqual(checkCopy([item], 'zh', resolve, [{...paragraph,
    cards: [{href: paragraph.cards[0].href, text: paragraph.cards[0].text}]}]), []);
  for (const patch of [
    {cards: []},
    {cards: [{text: '迅速了结', href: 'https://mtgch.com/card/WRONG/1/'}]},
    {decks: [{token, text: '某牌手', before: '：[', after: ']'}]},
    {text: '[[card:Dispatch|迅速了结]]'},
  ]) assert.ok(checkCopy([item], 'zh', resolve, [{...paragraph, ...patch}]).length);
});
