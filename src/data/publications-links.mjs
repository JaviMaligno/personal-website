// Pure store-link logic for the publications page.
// Lives in .mjs rather than .ts so `npm test` (node --test) can import it directly.

/** @typedef {'en' | 'es'} Lang */

const AMAZON_DOMAIN = { en: 'www.amazon.com', es: 'www.amazon.es' };

/**
 * Compose an Amazon product URL in the reader's marketplace.
 * Only ever called with a Kindle ASIN: print ASINs differ per marketplace,
 * so composing one for amazon.es from a KDP (US) ASIN would 404.
 *
 * @param {string | null | undefined} asin
 * @param {Lang} lang
 * @returns {string | null}
 */
export function amazonUrl(asin, lang) {
  if (!asin) return null;
  const domain = AMAZON_DOMAIN[lang] ?? AMAZON_DOMAIN.en;
  return `https://${domain}/dp/${asin}`;
}

/**
 * The edition of a book in the reader's language, or undefined if there is none.
 * Deliberately does not fall back to another language: showing an English cover
 * on the Spanish page without saying so would be worse than showing nothing.
 *
 * @template {{ editions: Array<{ lang: Lang }> }} B
 * @param {B} book
 * @param {Lang} lang
 * @returns {B['editions'][number] | undefined}
 */
export function getEdition(book, lang) {
  return book.editions.find((edition) => edition.lang === lang);
}

/**
 * Which store gets the main button and which gets the secondary link.
 * Payhip leads because it returns ~95% against Amazon's 70%; Amazon is
 * promoted to primary when an edition is not on Payhip, so a book on sale
 * can never render without a buy button.
 *
 * @param {{ payhip?: string, kindle?: string }} edition
 * @param {Lang} lang
 * @returns {{ primary: { store: 'payhip' | 'amazon', href: string } | null,
 *             secondary: { store: 'amazon', href: string } | null }}
 */
export function getStoreLinks(edition, lang) {
  const payhip = edition.payhip ?? null;
  const amazon = amazonUrl(edition.kindle, lang);

  if (payhip) {
    return {
      primary: { store: 'payhip', href: payhip },
      secondary: amazon ? { store: 'amazon', href: amazon } : null,
    };
  }
  if (amazon) {
    return { primary: { store: 'amazon', href: amazon }, secondary: null };
  }
  return { primary: null, secondary: null };
}
