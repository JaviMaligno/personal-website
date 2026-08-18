# Publications Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `/en/publications/` and `/es/publications/` — one page holding the two self-published books, the two arXiv preprints, the doctoral thesis and the teaching history — reachable from the main nav.

**Architecture:** Data lives in `src/data/publications.ts` (typed, imports cover images so Astro optimises them at build time). The pure store-link logic lives in `src/data/publications-links.mjs` so it can be unit-tested by the repo's existing `node --test` harness. Three section components render Books, Papers and Teaching; two thin page files (one per language) compose them and hand JSON-LD to `Layout` through a new optional prop. Prose is in the i18n JSON files; titles, ASINs and URLs are in the data file.

**Tech Stack:** Astro 5, TypeScript, `astro:assets` for cover optimisation, `node:test` for unit tests, JSON-LD for structured data.

**Spec:** `docs/superpowers/specs/2026-08-18-publications-page-design.md`

---

## File structure

| File | Responsibility |
| --- | --- |
| `src/data/publications-links.mjs` | Pure functions: pick the edition for a language, compose an Amazon URL, choose primary/secondary store. No imports, no framework. |
| `scripts/publications/store-links.test.mjs` | Unit tests for the above, run by `npm test`. |
| `src/data/publications.ts` | Types and data: books with per-language editions, research items, teaching items. Imports cover images. Builds the JSON-LD array. |
| `src/assets/publications/*.png` | The four cover images, optimised by Astro at build time. |
| `src/components/publications/BookCard.astro` | One book: cover, title, blurb, buy buttons. |
| `src/components/publications/PublicationsBooks.astro` | The Books section. |
| `src/components/publications/PublicationsPapers.astro` | The Papers section (preprints + thesis). |
| `src/components/publications/PublicationsTeaching.astro` | The Teaching section. |
| `src/pages/en/publications/index.astro` | English page. |
| `src/pages/es/publications/index.astro` | Spanish page. |
| `src/layouts/Layout.astro` | Modified: new `structuredData` prop, new nav entry. |
| `src/i18n/en.json`, `src/i18n/es.json` | Modified: `nav.publications` and a new `publications` block. |
| `src/components/mentoring/MentoringCTA.astro` | Modified: contextual link to the new page. |
| `scripts/publications/rendered-page.test.mjs` | Asserts the built HTML in `dist/` (run after `npm run build`). |

**Why covers go in `src/assets/` and not `public/`.** The four source files weigh 2.6–9.3 MB each. Served raw from `public/` that is ~24 MB on one page. Imported from `src/`, Astro's built-in sharp pipeline emits resized, modern-format versions at build time and the page ships a fraction of that. No new dependency: `astro:assets` is part of Astro 5.

---

## Task 1: Store-link helpers

**Files:**
- Create: `src/data/publications-links.mjs`
- Create: `scripts/publications/store-links.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `scripts/publications/store-links.test.mjs`:

```javascript
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
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npm test`

Expected: failure — `Cannot find module '.../src/data/publications-links.mjs'`.

- [ ] **Step 3: Write the implementation**

Create `src/data/publications-links.mjs`:

```javascript
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
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `npm test`

Expected: all tests pass, including the pre-existing `scripts/linkedin/utils.test.mjs`.

- [ ] **Step 5: Commit**

```bash
git add src/data/publications-links.mjs scripts/publications/store-links.test.mjs
git commit -m "feat: store-link helpers for the publications page"
```

---

## Task 2: Cover images

**Files:**
- Create: `src/assets/publications/logic-of-sacrifice-en.png`
- Create: `src/assets/publications/logic-of-sacrifice-es.png`
- Create: `src/assets/publications/science-catch-up-en.png`
- Create: `src/assets/publications/science-catch-up-es.png`

- [ ] **Step 1: Copy the four covers**

Run from the repo root:

```bash
mkdir -p src/assets/publications
cp "/c/Users/Usuario/GitHub/la-logica-del-sacrificio/traducciones/en/portada.png" src/assets/publications/logic-of-sacrifice-en.png
cp "/c/Users/Usuario/GitHub/la-logica-del-sacrificio/ensayo/portada.png" src/assets/publications/logic-of-sacrifice-es.png
cp public/blog/science-catch-up-cover-en.png src/assets/publications/science-catch-up-en.png
cp public/blog/science-catch-up-cover.png src/assets/publications/science-catch-up-es.png
```

- [ ] **Step 2: Confirm all four landed**

Run: `ls -l src/assets/publications/`

Expected: four `.png` files. They are large (2.6–9.3 MB) — that is fine, Astro resizes them at build time and only the optimised output ships.

- [ ] **Step 3: Commit**

```bash
git add src/assets/publications
git commit -m "assets: book covers for the publications page"
```

---

## Task 3: The data file

**Files:**
- Create: `src/data/publications.ts`

- [ ] **Step 1: Write the data file**

Create `src/data/publications.ts`:

```typescript
import type { ImageMetadata } from 'astro';
import type { Language } from '../i18n';
import { amazonUrl, getEdition, getStoreLinks } from './publications-links.mjs';

import logicOfSacrificeEn from '../assets/publications/logic-of-sacrifice-en.png';
import logicOfSacrificeEs from '../assets/publications/logic-of-sacrifice-es.png';
import scienceCatchUpEn from '../assets/publications/science-catch-up-en.png';
import scienceCatchUpEs from '../assets/publications/science-catch-up-es.png';

export { amazonUrl, getEdition, getStoreLinks };

export interface BookEdition {
  lang: Language;
  /** The published title of this edition. Never translated at render time. */
  title: string;
  cover: ImageMetadata;
  payhip?: string;
  /** Kindle ASIN — the only ASIN safe to compose per marketplace. */
  kindle?: string;
  /** Print ASINs are recorded but not linked: Amazon assigns them per marketplace. */
  paperback?: string;
  hardcover?: string;
  isbn?: string;
}

export interface Book {
  slug: string;
  /** i18n key under `publications.bookItems.<key>` */
  key: string;
  year: number;
  editions: BookEdition[];
  /** Blog slug, same in both languages. */
  relatedArticle?: string;
}

export interface ResearchItem {
  slug: string;
  /** i18n key under `publications.researchItems.<key>` */
  key: string;
  kind: 'preprint' | 'thesis';
  /** Published title. Not translated. */
  title: string;
  authors: string[];
  venue: string;
  year: number;
  url: string;
  doi?: string;
  relatedArticle?: string;
}

export interface TeachingItem {
  slug: string;
  /** i18n key under `publications.teachingItems.<key>` */
  key: string;
  institution: string;
  /** Omitted where the exact span is not confirmed. */
  years?: string;
}

export const books: Book[] = [
  {
    slug: 'logic-of-sacrifice',
    key: 'logicOfSacrifice',
    year: 2026,
    editions: [
      {
        lang: 'en',
        title: 'The Logic of Sacrifice',
        cover: logicOfSacrificeEn,
        payhip: 'https://payhip.com/b/sVI15',
        kindle: 'B0HBLBGHPF',
        paperback: 'B0HBLPHZD9',
        hardcover: 'B0HBNJ4MRD',
        isbn: '9798188990602',
      },
      {
        lang: 'es',
        title: 'La lógica del sacrificio',
        cover: logicOfSacrificeEs,
        payhip: 'https://payhip.com/b/ux0mB',
        kindle: 'B0H8M1W9SR',
        paperback: 'B0H958KHNW',
        hardcover: 'B0H961RXY2',
      },
    ],
  },
  {
    slug: 'science-catch-up',
    key: 'scienceCatchUp',
    year: 2026,
    relatedArticle: 'writing-an-essay-with-ai-codex-vs-claude-code',
    editions: [
      {
        lang: 'en',
        title: 'Science Catch-Up: When Science Finally Meets Reality',
        cover: scienceCatchUpEn,
        payhip: 'https://payhip.com/b/KHMxr',
      },
      {
        lang: 'es',
        title: 'Science Catch-Up: Cuando la ciencia se pone al día con la realidad',
        cover: scienceCatchUpEs,
        payhip: 'https://payhip.com/b/M4bjR',
        kindle: 'B0GSLHDCTK',
        paperback: 'B0GSS3224N',
        hardcover: 'B0GT3TS16R',
      },
    ],
  },
];

export const research: ResearchItem[] = [
  {
    slug: 'verified-world-model',
    key: 'verifiedWorldModel',
    kind: 'preprint',
    title: 'When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models',
    authors: ['Javier Aguilar Martín'],
    venue: 'arXiv (cs.AI, cs.LG)',
    year: 2026,
    url: 'https://arxiv.org/abs/2607.14169',
    relatedArticle: 'verified-world-model-still-loses',
  },
  {
    slug: 'derived-deligne-conjecture',
    key: 'derivedDeligne',
    kind: 'preprint',
    title: 'The Derived Deligne Conjecture',
    authors: ['Javier Aguilar Martín', 'Constanze Roitzheim'],
    venue: 'arXiv (math.RA)',
    year: 2024,
    url: 'https://arxiv.org/abs/2307.11414',
    doi: 'https://doi.org/10.48550/arXiv.2307.11414',
  },
  {
    slug: 'phd-thesis',
    key: 'thesis',
    kind: 'thesis',
    title: 'The Derived Deligne Conjecture',
    authors: ['Javier Aguilar Martín'],
    venue: 'University of Kent',
    year: 2023,
    url: 'https://kar.kent.ac.uk/105426/',
    doi: 'https://doi.org/10.22024/UniKent/01.02.105426',
  },
];

export const teaching: TeachingItem[] = [
  { slug: 'hesperides', key: 'hesperides', institution: 'Universidad de las Hespérides', years: '2026–' },
  { slug: 'kcl', key: 'kcl', institution: "King's College London" },
  { slug: 'kent', key: 'kent', institution: 'University of Kent' },
  { slug: 'keepcoding', key: 'keepcoding', institution: 'KeepCoding' },
];

const AUTHOR = { '@type': 'Person', name: 'Javier Aguilar Martín' } as const;

/**
 * JSON-LD for the whole page: one Book per edition on sale in this language,
 * one ScholarlyArticle per preprint, and the thesis.
 */
export function getPublicationsSchema(lang: Language): Record<string, unknown>[] {
  const bookSchemas = books.flatMap((book) => {
    const edition = getEdition(book, lang);
    if (!edition) return [];
    const { primary } = getStoreLinks(edition, lang);
    if (!primary) return [];
    return [
      {
        '@context': 'https://schema.org',
        '@type': 'Book',
        name: edition.title,
        author: AUTHOR,
        inLanguage: edition.lang,
        url: primary.href,
        ...(edition.isbn ? { isbn: edition.isbn } : {}),
        offers: {
          '@type': 'Offer',
          url: primary.href,
          availability: 'https://schema.org/InStock',
        },
      },
    ];
  });

  const researchSchemas = research.map((item) => ({
    '@context': 'https://schema.org',
    '@type': item.kind === 'thesis' ? 'Thesis' : 'ScholarlyArticle',
    headline: item.title,
    name: item.title,
    author: item.authors.map((name) => ({ '@type': 'Person', name })),
    datePublished: String(item.year),
    url: item.url,
    ...(item.doi ? { sameAs: item.doi } : {}),
    ...(item.kind === 'thesis' ? { inSupportOf: 'PhD in Mathematics' } : {}),
  }));

  return [...bookSchemas, ...researchSchemas];
}
```

- [ ] **Step 2: Verify it type-checks and the images resolve**

Run: `npx astro check`

Expected: no errors reported for `src/data/publications.ts`. Pre-existing errors elsewhere in the repo are not this task's concern — note them but do not fix them here.

Importing a `.mjs` file from TypeScript works here without any config change: `astro/tsconfigs/base` already sets `allowJs: true` and `moduleResolution: "Bundler"`, so the JSDoc annotations in `publications-links.mjs` are what types the helpers.

- [ ] **Step 3: Commit**

```bash
git add src/data/publications.ts
git commit -m "feat: publications data — books, preprints, thesis, teaching"
```

---

## Task 4: Translations

**Files:**
- Modify: `src/i18n/en.json`
- Modify: `src/i18n/es.json`

- [ ] **Step 1: Add the nav key to `src/i18n/en.json`**

Inside the existing `"nav"` object, after `"blog": "Blog",` add:

```json
    "publications": "Publications",
```

- [ ] **Step 2: Add the nav key to `src/i18n/es.json`**

Inside the existing `"nav"` object, after the `"blog"` entry, add:

```json
    "publications": "Publicaciones",
```

- [ ] **Step 3: Add the `publications` block to `src/i18n/en.json`**

As a new top-level key, after the existing `"blog"` block:

```json
  "publications": {
    "meta": {
      "title": "Publications - Javier Aguilar",
      "description": "Books, arXiv preprints, doctoral thesis and teaching by Javier Aguilar Martín."
    },
    "hero": {
      "title": "Publications",
      "subtitle": "Two books, two preprints, a doctoral thesis, and the teaching that came with them."
    },
    "books": {
      "title": "Books",
      "readArticle": "How I wrote it →"
    },
    "stores": {
      "payhip": "Buy on Payhip",
      "amazon": "Buy on Amazon",
      "alsoAmazon": "Also on Amazon — Kindle, paperback and hardcover"
    },
    "papers": {
      "title": "Papers",
      "preprintLabel": "Preprint",
      "thesisLabel": "PhD thesis",
      "readArticle": "Read the article →",
      "readPaper": "Read the paper →"
    },
    "teaching": {
      "title": "Teaching"
    },
    "bookItems": {
      "logicOfSacrifice": {
        "blurb": "Comfort is not the absence of cost, only its deferral. An essay on why voluntary hardship builds what comfort erodes, and what evolution and tradition already knew about it."
      },
      "scienceCatchUp": {
        "blurb": "Sixteen chapters on the limits of the scientific method: what it costs to wait for institutional consensus, and how to judge knowledge that has not been blessed yet."
      }
    },
    "researchItems": {
      "verifiedWorldModel": {
        "summary": "A language model can write a game's rules as executable code, score high on predicting the next state, and still lose. Accuracy is not adequacy for planning."
      },
      "derivedDeligne": {
        "summary": "Brace algebras on operads give derived A∞-algebras a conceptual home, and with it new, rigorous versions of the Deligne conjecture."
      },
      "thesis": {
        "summary": "Doctoral thesis, supervised by Constanze Roitzheim. The work the preprint above came out of."
      }
    },
    "teachingItems": {
      "hesperides": {
        "role": "Lecturer",
        "detail": "Algebra & Geometry — 6 ECTS first-year core course, shared by the BSc in Maths & Data Science and Maths & Philosophy."
      },
      "kcl": {
        "role": "Graduate Teaching Assistant",
        "detail": "Undergraduate mathematics."
      },
      "kent": {
        "role": "Graduate Teaching Assistant",
        "detail": "Undergraduate mathematics, alongside the PhD."
      },
      "keepcoding": {
        "role": "Bootcamp instructor",
        "detail": "Statistical methods in R."
      }
    }
  },
```

- [ ] **Step 4: Add the `publications` block to `src/i18n/es.json`**

As a new top-level key, in the same position as in `en.json`:

```json
  "publications": {
    "meta": {
      "title": "Publicaciones - Javier Aguilar",
      "description": "Libros, preprints en arXiv, tesis doctoral y docencia de Javier Aguilar Martín."
    },
    "hero": {
      "title": "Publicaciones",
      "subtitle": "Dos libros, dos preprints, una tesis doctoral y la docencia que vino con ellos."
    },
    "books": {
      "title": "Libros",
      "readArticle": "Cómo lo escribí →"
    },
    "stores": {
      "payhip": "Comprar en Payhip",
      "amazon": "Comprar en Amazon",
      "alsoAmazon": "También en Amazon — Kindle, tapa blanda y tapa dura"
    },
    "papers": {
      "title": "Papers",
      "preprintLabel": "Preprint",
      "thesisLabel": "Tesis doctoral",
      "readArticle": "Leer el artículo →",
      "readPaper": "Leer el paper →"
    },
    "teaching": {
      "title": "Docencia"
    },
    "bookItems": {
      "logicOfSacrifice": {
        "blurb": "La comodidad no elimina el coste, solo lo aplaza. Un ensayo sobre por qué la dificultad voluntaria construye lo que la comodidad erosiona, y sobre lo que la evolución y la tradición ya sabían de esto."
      },
      "scienceCatchUp": {
        "blurb": "Dieciséis capítulos sobre los límites del método científico: lo que cuesta esperar al consenso institucional, y cómo juzgar el conocimiento que todavía no ha recibido su bendición."
      }
    },
    "researchItems": {
      "verifiedWorldModel": {
        "summary": "Un modelo de lenguaje puede escribir las reglas de un juego como código ejecutable, acertar al predecir el siguiente estado y aun así perder. Acertar no es bastar para planificar."
      },
      "derivedDeligne": {
        "summary": "Las álgebras brace sobre operads dan a las álgebras A∞ derivadas un marco conceptual propio, y con él versiones nuevas y rigurosas de la conjetura de Deligne."
      },
      "thesis": {
        "summary": "Tesis doctoral, dirigida por Constanze Roitzheim. El trabajo del que salió el preprint anterior."
      }
    },
    "teachingItems": {
      "hesperides": {
        "role": "Profesor principal",
        "detail": "Álgebra y Geometría — asignatura básica de 6 ECTS de primer curso, compartida por los grados de Matemáticas y Ciencia de Datos y de Matemáticas y Filosofía."
      },
      "kcl": {
        "role": "Graduate Teaching Assistant",
        "detail": "Matemáticas de grado."
      },
      "kent": {
        "role": "Graduate Teaching Assistant",
        "detail": "Matemáticas de grado, en paralelo al doctorado."
      },
      "keepcoding": {
        "role": "Profesor de bootcamp",
        "detail": "Métodos estadísticos en R."
      }
    }
  },
```

- [ ] **Step 5: Verify both files are still valid JSON**

Run: `node -e "const en=require('./src/i18n/en.json'), es=require('./src/i18n/es.json'); const ka=Object.keys(en.publications).sort(), kb=Object.keys(es.publications).sort(); console.log(JSON.stringify(ka)===JSON.stringify(kb) ? 'keys match' : 'KEY MISMATCH'); console.log(en.nav.publications, '|', es.nav.publications);"`

Expected output:

```
keys match
Publications | Publicaciones
```

- [ ] **Step 6: Commit**

```bash
git add src/i18n/en.json src/i18n/es.json
git commit -m "i18n: strings for the publications page"
```

---

## Task 5: Book card and Books section

**Files:**
- Create: `src/components/publications/BookCard.astro`
- Create: `src/components/publications/PublicationsBooks.astro`

- [ ] **Step 1: Write `src/components/publications/BookCard.astro`**

```astro
---
import { Image } from 'astro:assets';
import { getLangFromUrl, useTranslations, getLocalizedPath, type Language } from '../../i18n';
import { getEdition, getStoreLinks, type Book } from '../../data/publications';

interface Props {
  book: Book;
}

const { book } = Astro.props;
const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const p = t('publications');

const edition = getEdition(book, lang);
const links = edition ? getStoreLinks(edition, lang) : { primary: null, secondary: null };
const articleHref = book.relatedArticle
  ? `${getLocalizedPath('/blog/', lang)}${book.relatedArticle}/`
  : null;
---

{edition && (
  <article class="card book-card">
    <div class="book-cover">
      <Image src={edition.cover} alt={edition.title} width={320} densities={[1, 2]} loading="lazy" />
    </div>
    <div class="book-body">
      <h3>{edition.title}</h3>
      <p class="blurb">{p.bookItems[book.key].blurb}</p>
      <div class="book-actions">
        {links.primary && (
          <a href={links.primary.href} target="_blank" rel="noopener" class="btn btn-primary">
            {links.primary.store === 'payhip' ? p.stores.payhip : p.stores.amazon}
          </a>
        )}
        {links.secondary && (
          <a href={links.secondary.href} target="_blank" rel="noopener" class="secondary-store">
            {p.stores.alsoAmazon}
          </a>
        )}
      </div>
      {articleHref && <a href={articleHref} class="related-article">{p.books.readArticle}</a>}
    </div>
  </article>
)}

<style>
  .book-card {
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: var(--space-lg);
    align-items: start;
  }
  .book-cover img {
    width: 100%;
    height: auto;
    border-radius: var(--radius-md);
    display: block;
  }
  .book-body h3 {
    font-size: 1.375rem;
    margin-bottom: var(--space-sm);
  }
  .blurb {
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: var(--space-md);
  }
  .book-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-md);
  }
  .secondary-store {
    color: var(--text-muted);
    font-size: 0.9375rem;
    text-decoration: none;
    transition: color var(--transition-base);
  }
  .secondary-store:hover {
    color: var(--accent-text);
  }
  .related-article {
    display: inline-block;
    margin-top: var(--space-md);
    color: var(--text-muted);
    font-size: 0.9375rem;
    text-decoration: none;
    transition: color var(--transition-base);
  }
  .related-article:hover {
    color: var(--accent-text);
  }

  @media (max-width: 768px) {
    .book-card {
      grid-template-columns: 1fr;
    }
    .book-cover {
      max-width: 220px;
      margin: 0 auto;
    }
    .book-actions {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
```

- [ ] **Step 2: Write `src/components/publications/PublicationsBooks.astro`**

```astro
---
import { getLangFromUrl, useTranslations, type Language } from '../../i18n';
import { books } from '../../data/publications';
import BookCard from './BookCard.astro';

const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const p = t('publications');
---

<section id="books" class="publications-books">
  <div class="container">
    <h2>{p.books.title}</h2>
    <div class="book-list">
      {books.map((book) => <BookCard book={book} />)}
    </div>
  </div>
</section>

<style>
  .publications-books {
    padding: var(--space-xl) 0;
  }
  h2 {
    font-size: 1.75rem;
    margin-bottom: var(--space-lg);
  }
  .book-list {
    display: grid;
    gap: var(--space-lg);
  }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add src/components/publications/BookCard.astro src/components/publications/PublicationsBooks.astro
git commit -m "feat: book card and books section for the publications page"
```

---

## Task 6: Papers section

**Files:**
- Create: `src/components/publications/PublicationsPapers.astro`

- [ ] **Step 1: Write `src/components/publications/PublicationsPapers.astro`**

```astro
---
import { getLangFromUrl, useTranslations, getLocalizedPath, type Language } from '../../i18n';
import { research } from '../../data/publications';

const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const p = t('publications');
---

<section id="papers" class="publications-papers">
  <div class="container">
    <h2>{p.papers.title}</h2>
    <ul class="paper-list">
      {research.map((item) => (
        <li class="card paper">
          <div class="paper-head">
            <span class="kind" data-kind={item.kind}>
              {item.kind === 'thesis' ? p.papers.thesisLabel : p.papers.preprintLabel}
            </span>
            <span class="meta">{item.venue} · {item.year}</span>
          </div>
          <h3>{item.title}</h3>
          <p class="authors">{item.authors.join(', ')}</p>
          <p class="summary">{p.researchItems[item.key].summary}</p>
          <div class="paper-links">
            <a href={item.url} target="_blank" rel="noopener" class="paper-link">{p.papers.readPaper}</a>
            {item.relatedArticle && (
              <a href={`${getLocalizedPath('/blog/', lang)}${item.relatedArticle}/`} class="paper-link">
                {p.papers.readArticle}
              </a>
            )}
          </div>
        </li>
      ))}
    </ul>
  </div>
</section>

<style>
  .publications-papers {
    padding: var(--space-xl) 0;
  }
  h2 {
    font-size: 1.75rem;
    margin-bottom: var(--space-lg);
  }
  .paper-list {
    list-style: none;
    padding: 0;
    display: grid;
    gap: var(--space-md);
  }
  .paper-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-xs);
  }
  .kind {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.2rem 0.6rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--glass-border);
    color: var(--text-muted);
  }
  .kind[data-kind='thesis'] {
    color: var(--accent-text);
    border-color: var(--accent-text);
  }
  .meta {
    font-size: 0.875rem;
    color: var(--text-muted);
  }
  .paper h3 {
    font-size: 1.125rem;
    line-height: 1.4;
    margin-bottom: var(--space-xs);
  }
  .authors {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: var(--space-sm);
  }
  .summary {
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: var(--space-md);
  }
  .paper-links {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-md);
  }
  .paper-link {
    color: var(--text-muted);
    font-size: 0.9375rem;
    text-decoration: none;
    transition: color var(--transition-base);
  }
  .paper-link:hover {
    color: var(--accent-text);
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/publications/PublicationsPapers.astro
git commit -m "feat: papers section for the publications page"
```

---

## Task 7: Teaching section

**Files:**
- Create: `src/components/publications/PublicationsTeaching.astro`

- [ ] **Step 1: Write `src/components/publications/PublicationsTeaching.astro`**

```astro
---
import { getLangFromUrl, useTranslations, type Language } from '../../i18n';
import { teaching } from '../../data/publications';

const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const p = t('publications');
---

<section id="teaching" class="publications-teaching">
  <div class="container">
    <h2>{p.teaching.title}</h2>
    <ul class="teaching-list">
      {teaching.map((item) => (
        <li class="teaching-item">
          <div class="teaching-head">
            <span class="institution">{item.institution}</span>
            {item.years && <span class="years">{item.years}</span>}
          </div>
          <p class="role">{p.teachingItems[item.key].role}</p>
          <p class="detail">{p.teachingItems[item.key].detail}</p>
        </li>
      ))}
    </ul>
  </div>
</section>

<style>
  .publications-teaching {
    padding: var(--space-xl) 0 var(--space-3xl);
  }
  h2 {
    font-size: 1.75rem;
    margin-bottom: var(--space-lg);
  }
  .teaching-list {
    list-style: none;
    padding: 0;
    display: grid;
    gap: var(--space-md);
  }
  .teaching-item {
    padding-bottom: var(--space-md);
    border-bottom: 1px solid var(--glass-border);
  }
  .teaching-item:last-child {
    border-bottom: none;
  }
  .teaching-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--space-sm);
  }
  .institution {
    font-weight: 600;
  }
  .years {
    font-size: 0.875rem;
    color: var(--text-muted);
  }
  .role {
    color: var(--accent-text);
    font-size: 0.9375rem;
    margin: var(--space-xs) 0;
  }
  .detail {
    color: var(--text-secondary);
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/publications/PublicationsTeaching.astro
git commit -m "feat: teaching section for the publications page"
```

---

## Task 8: Layout — nav entry and structured-data prop

**Files:**
- Modify: `src/layouts/Layout.astro`

- [ ] **Step 1: Add the prop to the interface**

Replace the existing `Props` interface and destructuring (near line 5) with:

```astro
interface Props {
  title?: string;
  description?: string;
  langSwitchOverride?: string;
  structuredData?: Record<string, unknown>[];
}

const { title = 'AGILabs - AI Agent Architecture & Multi-Agent Systems', description = 'I design AI systems that actually work. Multi-agent orchestration, MCP development, and compliance automation.', langSwitchOverride, structuredData = [] } = Astro.props;
```

- [ ] **Step 2: Render the extra schema in `<head>`**

Directly after the three existing schema scripts (`organizationSchema` is the last, around line 146), add:

```astro
    {structuredData.map((schema) => (
      <script type="application/ld+json" set:html={JSON.stringify(schema)} />
    ))}
```

- [ ] **Step 3: Add the nav entry**

In the `<nav class="nav">` block, immediately after the Blog link, add:

```astro
          <a href={getLocalizedPath('/publications/', lang)}>{t('nav').publications}</a>
```

- [ ] **Step 4: Verify the nav renders in both languages**

Run: `npm run build`

Then: `grep -c "publications/" dist/en/index.html dist/es/index.html`

Expected: a non-zero count for both files.

- [ ] **Step 5: Commit**

```bash
git add src/layouts/Layout.astro
git commit -m "feat: publications nav entry and per-page structured data"
```

---

## Task 9: The two pages

**Files:**
- Create: `src/pages/en/publications/index.astro`
- Create: `src/pages/es/publications/index.astro`

- [ ] **Step 1: Write `src/pages/en/publications/index.astro`**

```astro
---
import Layout from '../../../layouts/Layout.astro';
import PublicationsBooks from '../../../components/publications/PublicationsBooks.astro';
import PublicationsPapers from '../../../components/publications/PublicationsPapers.astro';
import PublicationsTeaching from '../../../components/publications/PublicationsTeaching.astro';
import { useTranslations } from '../../../i18n';
import { getPublicationsSchema } from '../../../data/publications';

const lang = 'en';
const t = useTranslations(lang);
const p = t('publications');
const schema = getPublicationsSchema(lang);
---

<Layout title={p.meta.title} description={p.meta.description} structuredData={schema}>
  <div class="publications-page">
    <div class="container">
      <header class="page-header">
        <h1>{p.hero.title}</h1>
        <p>{p.hero.subtitle}</p>
      </header>
    </div>
    <PublicationsBooks />
    <PublicationsPapers />
    <PublicationsTeaching />
  </div>
</Layout>

<style>
  .publications-page {
    padding-top: var(--space-3xl);
  }
  .page-header {
    max-width: 720px;
    margin-bottom: var(--space-xl);
  }
  .page-header h1 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin-bottom: var(--space-sm);
  }
  .page-header p {
    color: var(--text-secondary);
    font-size: 1.125rem;
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 2: Write `src/pages/es/publications/index.astro`**

Identical except for the language constant:

```astro
---
import Layout from '../../../layouts/Layout.astro';
import PublicationsBooks from '../../../components/publications/PublicationsBooks.astro';
import PublicationsPapers from '../../../components/publications/PublicationsPapers.astro';
import PublicationsTeaching from '../../../components/publications/PublicationsTeaching.astro';
import { useTranslations } from '../../../i18n';
import { getPublicationsSchema } from '../../../data/publications';

const lang = 'es';
const t = useTranslations(lang);
const p = t('publications');
const schema = getPublicationsSchema(lang);
---

<Layout title={p.meta.title} description={p.meta.description} structuredData={schema}>
  <div class="publications-page">
    <div class="container">
      <header class="page-header">
        <h1>{p.hero.title}</h1>
        <p>{p.hero.subtitle}</p>
      </header>
    </div>
    <PublicationsBooks />
    <PublicationsPapers />
    <PublicationsTeaching />
  </div>
</Layout>

<style>
  .publications-page {
    padding-top: var(--space-3xl);
  }
  .page-header {
    max-width: 720px;
    margin-bottom: var(--space-xl);
  }
  .page-header h1 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin-bottom: var(--space-sm);
  }
  .page-header p {
    color: var(--text-secondary);
    font-size: 1.125rem;
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 3: Build and eyeball both pages**

Run: `npm run build && npm run preview`

Open `http://localhost:4321/en/publications/` and `http://localhost:4321/es/publications/`.

Expected: both books with covers, four buy affordances (Payhip on all four editions, "Also on Amazon" on the three editions that have a Kindle ASIN — the English *Science Catch-Up* has none), three papers, four teaching entries. Stop the preview with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add src/pages/en/publications/index.astro src/pages/es/publications/index.astro
git commit -m "feat: publications pages in both languages"
```

---

## Task 10: Link from the mentoring page

**Files:**
- Modify: `src/components/mentoring/MentoringCTA.astro`
- Modify: `src/i18n/en.json`, `src/i18n/es.json`

- [ ] **Step 1: Add the link text to `src/i18n/en.json`**

Inside `mentoring.cta`, after `"button": "Book a call"`, add:

```json
      "publicationsLink": "Or read what I have written and taught →"
```

- [ ] **Step 2: Add the link text to `src/i18n/es.json`**

Inside `mentoring.cta`, after the `"button"` entry, add:

```json
      "publicationsLink": "O lee lo que he escrito y enseñado →"
```

- [ ] **Step 3: Render the link in `src/components/mentoring/MentoringCTA.astro`**

Replace the frontmatter with:

```astro
---
import { getLangFromUrl, useTranslations, getLocalizedPath, type Language } from '../../i18n';

const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const cta = t('mentoring').cta;
const publicationsPath = getLocalizedPath('/publications/', lang);
---
```

Then, immediately after the closing `</a>` of the Calendly button and before `</div>`, add:

```astro
      <p class="secondary-link">
        <a href={publicationsPath}>{cta.publicationsLink}</a>
      </p>
```

And append to the component's `<style>` block:

```css
  .secondary-link {
    margin-top: var(--space-md);
    margin-bottom: 0;
    font-size: 0.9375rem;
  }
  .secondary-link a {
    color: var(--text-muted);
    text-decoration: none;
    transition: color var(--transition-base);
  }
  .secondary-link a:hover {
    color: var(--accent-text);
  }
```

- [ ] **Step 4: Verify**

Run: `npm run build && grep -c "publications/" dist/en/mentoring/index.html`

Expected: at least 2 (the nav entry plus the CTA link).

- [ ] **Step 5: Commit**

```bash
git add src/components/mentoring/MentoringCTA.astro src/i18n/en.json src/i18n/es.json
git commit -m "feat: link the mentoring CTA to the publications page"
```

---

## Task 11: Rendered-page assertions

**Files:**
- Create: `scripts/publications/rendered-page.test.mjs`

This is the regression net for the parts unit tests cannot reach: that the Spanish page really links `amazon.es`, that the English one links `amazon.com`, and that the edition with no Amazon listing renders no Amazon link.

- [ ] **Step 1: Write the failing test**

Create `scripts/publications/rendered-page.test.mjs`:

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const EN = 'dist/en/publications/index.html';
const ES = 'dist/es/publications/index.html';

function read(path) {
  assert.ok(existsSync(path), `${path} is missing — run "npm run build" first`);
  return readFileSync(path, 'utf8');
}

test('the English page links Payhip for every edition', () => {
  const html = read(EN);
  assert.ok(html.includes('https://payhip.com/b/sVI15'), 'The Logic of Sacrifice (en)');
  assert.ok(html.includes('https://payhip.com/b/KHMxr'), 'Science Catch-Up (en)');
});

test('the Spanish page links the Spanish editions, not the English ones', () => {
  const html = read(ES);
  assert.ok(html.includes('https://payhip.com/b/ux0mB'), 'La lógica del sacrificio');
  assert.ok(html.includes('https://payhip.com/b/M4bjR'), 'Science Catch-Up (es)');
  assert.ok(!html.includes('https://payhip.com/b/sVI15'), 'no English edition leaks in');
});

test('Amazon links use the reader marketplace', () => {
  assert.ok(read(EN).includes('https://www.amazon.com/dp/B0HBLBGHPF'), 'en → amazon.com');
  assert.ok(read(ES).includes('https://www.amazon.es/dp/B0H8M1W9SR'), 'es → amazon.es');
});

test('no print ASIN is ever composed into a URL', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    for (const asin of ['B0HBLPHZD9', 'B0HBNJ4MRD', 'B0H958KHNW', 'B0H961RXY2', 'B0GSS3224N', 'B0GT3TS16R']) {
      assert.ok(!html.includes(`/dp/${asin}`), `${asin} must not be linked in ${path}`);
    }
  }
});

test('the English Science Catch-Up shows no Amazon link', () => {
  const html = read(EN);
  const amazonLinks = html.match(/https:\/\/www\.amazon\.com\/dp\/\w+/g) ?? [];
  assert.deepEqual([...new Set(amazonLinks)], ['https://www.amazon.com/dp/B0HBLBGHPF']);
});

test('both pages carry the papers, the thesis and the teaching entries', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    assert.ok(html.includes('https://arxiv.org/abs/2607.14169'), `verified world model preprint in ${path}`);
    assert.ok(html.includes('https://arxiv.org/abs/2307.11414'), `derived Deligne preprint in ${path}`);
    assert.ok(html.includes('https://kar.kent.ac.uk/105426/'), `thesis in ${path}`);
    assert.ok(html.includes('KeepCoding'), `teaching list in ${path}`);
  }
});

test('both pages emit Book and ScholarlyArticle structured data', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    assert.ok(html.includes('"@type":"Book"'), `Book schema in ${path}`);
    assert.ok(html.includes('"@type":"ScholarlyArticle"'), `ScholarlyArticle schema in ${path}`);
    assert.ok(html.includes('"@type":"Thesis"'), `Thesis schema in ${path}`);
  }
});
```

- [ ] **Step 2: Run it against a stale build and watch it fail**

Run: `rm -rf dist && npm test`

Expected: failures saying `dist/en/publications/index.html is missing — run "npm run build" first`. This proves the assertions are actually reading the build output rather than passing vacuously.

- [ ] **Step 3: Build and run the tests**

Run: `npm run build && npm test`

Expected: every test passes, including the two pre-existing suites.

- [ ] **Step 4: Commit**

```bash
git add scripts/publications/rendered-page.test.mjs
git commit -m "test: assert the rendered publications pages"
```

---

## Task 12: Final verification

- [ ] **Step 1: Clean build**

Run: `rm -rf dist && npm run build && npm test`

Expected: build succeeds, all tests pass.

- [ ] **Step 2: Check the shipped image weight**

Run: `ls -lS dist/_astro/ | head -10`

Expected: the largest emitted asset is well under 1 MB — the four covers enter the build at 2.6–9.3 MB and must not leave it that way. If any single image is larger than 1 MB, lower the `width` in `BookCard.astro` from 320 to 240 and rebuild.

- [ ] **Step 3: Confirm the sitemap picked the pages up**

Run: `grep -c "publications" dist/sitemap-0.xml`

Expected: at least 2.

- [ ] **Step 4: Visual pass**

Run: `npm run preview` and check `/en/publications/` and `/es/publications/` at desktop and mobile widths. Confirm the covers are not stretched, the buy buttons wrap rather than overflow on a narrow screen, and the nav entry appears in both languages.

- [ ] **Step 5: Commit anything outstanding and push the branch**

```bash
git status
git push -u origin HEAD
```

---

## Deliberately out of scope

- Talks, slides, video.
- A detail page per publication.
- Direct paperback/hardcover buttons — print ASINs differ per marketplace, so the page links the Kindle edition and lets Amazon's own format selector serve the reader's store. The print ASINs are in the data file for the day this changes.
- Years for the King's College London, Kent and KeepCoding teaching entries: not confirmed, so the `years` field is left off rather than guessed. Adding them later is one field per entry.
