import { test } from 'node:test';
import assert from 'node:assert/strict';
import { amazonUrl, getEdition, getStoreLinks } from '../../src/data/publications-links.mjs';

const englishEdition = {
  lang: 'en',
  title: 'The Logic of Sacrifice',
  payhip: 'https://payhip.com/b/sVI15',
  kindle: 'B0HBLBGHPF',
};

const spanishEdition = {
  lang: 'es',
  title: 'La lógica del sacrificio',
  payhip: 'https://payhip.com/b/ux0mB',
  kindle: 'B0H8M1W9SR',
};

const book = { slug: 'logic-of-sacrifice', editions: [englishEdition, spanishEdition] };

test('amazonUrl uses the reader marketplace', () => {
  assert.equal(amazonUrl('B0HBLBGHPF', 'en'), 'https://www.amazon.com/dp/B0HBLBGHPF');
  assert.equal(amazonUrl('B0HBLBGHPF', 'es'), 'https://www.amazon.es/dp/B0HBLBGHPF');
});

test('amazonUrl returns null when there is no ASIN', () => {
  assert.equal(amazonUrl(undefined, 'en'), null);
  assert.equal(amazonUrl(null, 'es'), null);
});

test('getEdition picks the edition matching the language', () => {
  assert.equal(getEdition(book, 'es'), spanishEdition);
  assert.equal(getEdition(book, 'en'), englishEdition);
});

test('getEdition returns undefined when the language is missing', () => {
  const englishOnly = { slug: 'science-catch-up', editions: [englishEdition] };
  assert.equal(getEdition(englishOnly, 'es'), undefined);
});

test('getStoreLinks puts Payhip first and Amazon second', () => {
  const links = getStoreLinks(spanishEdition, 'es');
  assert.deepEqual(links.primary, { store: 'payhip', href: 'https://payhip.com/b/ux0mB' });
  assert.deepEqual(links.secondary, { store: 'amazon', href: 'https://www.amazon.es/dp/B0H8M1W9SR' });
});

test('getStoreLinks has no secondary when the edition is not on Amazon', () => {
  const payhipOnly = { lang: 'en', title: 'Science Catch-Up', payhip: 'https://payhip.com/b/KHMxr' };
  const links = getStoreLinks(payhipOnly, 'en');
  assert.deepEqual(links.primary, { store: 'payhip', href: 'https://payhip.com/b/KHMxr' });
  assert.equal(links.secondary, null);
});

test('getStoreLinks promotes Amazon when there is no Payhip link', () => {
  const amazonOnly = { lang: 'en', title: 'Future book', kindle: 'B000000000' };
  const links = getStoreLinks(amazonOnly, 'en');
  assert.deepEqual(links.primary, { store: 'amazon', href: 'https://www.amazon.com/dp/B000000000' });
  assert.equal(links.secondary, null);
});

test('getStoreLinks returns no links when the edition is not on sale anywhere', () => {
  const links = getStoreLinks({ lang: 'en', title: 'Unsold' }, 'en');
  assert.equal(links.primary, null);
  assert.equal(links.secondary, null);
});
