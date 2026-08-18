# Publications page — design

**Date:** 2026-08-18
**Issue:** [#54 — Centralizar el trabajo académico y docente en la web](https://github.com/JaviMaligno/personal-website/issues/54)
**Status:** approved design, pending implementation plan

## Problem

Javier's books, preprints, doctoral thesis and teaching history live nowhere on
javieraguilar.ai. The mentoring offer at `/mentoring` rests on the claim that he
teaches this material, and today that claim is backed only by blog articles. The
academic and authorial record would reinforce it, and two self-published books
have no sales surface at all on his own site.

## Goals

1. One page that holds books, research and teaching, reachable from the main nav.
2. Sell the books — cover, blurb and a buy button per book, in the reader's language.
3. Establish credibility — preprints, thesis and teaching visible as a record.
4. Survive change: each book edition sells on a different, shifting set of stores.

## Non-goals

- Talks, slides and video. Explicitly out of scope (decided 2026-08-18).
- A per-publication detail page. Every item links out to arXiv, KAR, Payhip or Amazon.
- A full academic CV. This is a curated page, not a résumé dump.
- Any change to `/skills` — that page is the Claude skills catalogue and does not overlap.

## Route and navigation

- `src/pages/en/publications/index.astro` and `src/pages/es/publications/index.astro`.
- New main-nav entry between **Blog** and **Proceso**, using a new `nav.publications`
  key in `src/i18n/en.json` and `es.json`. The nav goes from 6 links to 7 plus the
  call CTA; on mobile it is already a collapsing menu, so it fits.
- A contextual link from `/mentoring` to `/publications` — the path that turns
  credibility into the offer.

## Data model

New file `src/data/publications.ts`, following the pattern of `src/data/projects.ts`:
data in TypeScript, prose in the i18n JSON files.

```ts
type Lang = 'en' | 'es';

interface BookEdition {
  lang: Lang;
  title: string;
  cover: string;          // path under /publications/
  payhip?: string;        // full URL
  kindle?: string;        // ASIN
  paperback?: string;     // ASIN
  hardcover?: string;     // ASIN
  isbn?: string;
}

interface Book {
  key: string;            // i18n key for blurb
  year: number;
  editions: BookEdition[];
  relatedArticle?: string; // blog slug
}

interface ResearchItem {
  key: string;            // i18n key for the one-line summary
  kind: 'preprint' | 'thesis';
  title: string;          // published title, not translated
  authors: string[];
  venue: string;          // 'arXiv (math.RA)', 'University of Kent'
  year: number;
  url: string;
  doi?: string;
  relatedArticle?: string;
}

interface TeachingItem {
  key: string;
  institution: string;
  years: string;          // '2026–', '2019–2022'
}
```

**Why the store links are optional.** All four editions are live on Payhip today
(confirmed 2026-08-18 against the store page), but the Amazon side is uneven: the
formats on sale differ per edition, some ASINs are still unknown, and the book
repo's own metadata files lag reality — they still describe *The Logic of Sacrifice*
as blocked from Payhip by KDP Select. Optional fields make a partially-known edition
the normal case rather than an exception, and adding a store later is one line of data.

**Amazon URLs are built from the ASIN, not stored whole.** An ASIN is the same
across marketplaces, so the page composes `amazon.es/dp/<ASIN>` on `/es` and
`amazon.com/dp/<ASIN>` on `/en`. One field per format, two working links.

### Confirmed data (2026-08-18)

Payhip store: <https://payhip.com/DrJavierAguilarMartn>

| Book | Lang | Title | Payhip |
| --- | --- | --- | --- |
| The Logic of Sacrifice | en | *The Logic of Sacrifice* | `payhip.com/b/sVI15` |
| La lógica del sacrificio | es | *La lógica del sacrificio* | `payhip.com/b/ux0mB` |
| Science Catch-Up | en | *Science Catch-Up: When Science Finally Meets Reality* | `payhip.com/b/KHMxr` |
| Science Catch-Up | es | *Science Catch-Up: Cuando la ciencia se pone al día con la realidad* | `payhip.com/b/M4bjR` |

Amazon ASINs known so far: `B0GSVFPF2N` (Science Catch-Up, edition language to
confirm), `B0HBLBGHPF` (The Logic of Sacrifice EN, Kindle), `B0HBLPHZD9` (same,
paperback). Both books also have a hardcover on sale; those ASINs are still missing.
Print ISBNs for the English *Logic of Sacrifice*: 9798188990602 (paperback),
9798189013126 (hardcover).

## Page structure

Three sections, in this order, each with its own heading.

### 1. Books

Card per book: cover image, title, blurb, buy buttons.

- The reader's language selects the edition. `/es/publications` shows the Spanish
  edition; `/en/publications` the English one. Both books exist in both languages,
  so there is no missing-edition fallback and no "coming soon" state — deliberately
  left out rather than built for a case that does not exist. Add it the day a book
  launches in one language only.
- **Buy button order:** Payhip is the primary button (≈95% royalty vs 70% on
  Amazon); Amazon is a secondary link. When an edition has no Payhip link, Amazon
  becomes the primary button. Print formats (paperback, hardcover) are secondary
  links when present.
- *Science Catch-Up* links to the blog article about writing it with AI
  (`writing-an-essay-with-ai-codex-vs-claude-code`).

### 2. Papers

One row per item, newest first: title, authors, venue, year, link.

- *When a Verified World Model Still Loses* — arXiv:2607.14169, cs.AI/cs.LG, 2026,
  sole author. Links to arXiv **and** to its blog article
  (`verified-world-model-still-loses`).
- *The Derived Deligne Conjecture* — arXiv:2307.11414, math.RA, with Constanze
  Roitzheim, v3 2024.
- **Doctoral thesis** — *The Derived Deligne Conjecture*, PhD Mathematics,
  University of Kent, June 2023, supervised by Constanze Roitzheim.
  [KAR 105426](https://kar.kent.ac.uk/105426/), DOI 10.22024/UniKent/01.02.105426.

The thesis sits in this section rather than in its own, marked by its `kind` field.

The link from the 2026 preprint to its blog article is load-bearing: without it the
two preprints read as the work of two unrelated people — a category-theory
mathematician and an AI engineer. The article is what connects them.

### 3. Teaching

A plain list — institution, role, subject, years. No prose blocks.

- Universidad de las Hespérides — lecturer, Algebra & Geometry (6 ECTS, first year), 2026–
- King's College London — Graduate Teaching Assistant
- University of Kent — Graduate Teaching Assistant
- KeepCoding — bootcamp instructor, statistical methods in R

## Content and i18n

All prose (blurbs, section headings, role descriptions, the "English edition" note)
goes under a new `publications` key in `src/i18n/en.json` and `es.json`. Titles of
books and papers are **not** translated: they are the published titles, and each
book edition carries its own real title.

## Images

Book covers copied into `public/publications/`:

- *La lógica del sacrificio* — from `la-logica-del-sacrificio/ensayo/portada.png`
  (ES) and `traducciones/en/portada.png` (EN).
- *Science Catch-Up* — already in the repo at `public/blog/science-catch-up-cover.png`
  (ES) and `science-catch-up-cover-en.png` (EN); copied to `public/publications/`
  so the blog and the publications page do not share mutable assets.

## Structured data

`schema.org` JSON-LD on the page:

- `Book` for each book, with `author`, `inLanguage`, `isbn` where known, and `offers`
  pointing at the buy URL.
- `ScholarlyArticle` for each preprint, with `author`, `identifier` (the arXiv id)
  and `sameAs` (the DOI).
- The thesis as `Thesis` with `inSupportOf` the PhD.

Cheap to add, and without it a search engine reads the page as undifferentiated text
and never connects Javier to the authorship.

## Testing

The site has no test suite for pages; verification is a build plus a visual check.

- `npm run build` must pass with no new warnings.
- Both `/en/publications/` and `/es/publications/` render, and the nav entry appears
  on every page in both languages.
- Each buy button resolves to a live URL (manual click-through once), including the
  composed `amazon.es` / `amazon.com` variants of every ASIN.

## Open data gaps

These block content, not design. Amazon blocks automated fetching and the books are
too recent to be indexed by search engines, so the remaining ASINs have to come from
Javier's KDP bookshelf:

1. Which edition is `B0GSVFPF2N` — the English or the Spanish *Science Catch-Up*?
2. The ASIN of the other *Science Catch-Up* edition.
3. The ASIN of *La lógica del sacrificio* (ES) on Amazon, if it is there.
4. Hardcover ASINs for both books (he confirmed both have one on sale).
5. Paperback ASIN for any edition beyond the English *Logic of Sacrifice*.

Until each gap is closed, the corresponding format link stays absent from the data
file — which the design already handles. Payhip covers all four editions today, so
the page ships complete and sellable even with every Amazon gap still open.
