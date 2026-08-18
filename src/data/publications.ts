import type { ImageMetadata } from 'astro';
import type { Language } from '../i18n';
import { amazonUrl, getEdition, getStoreLinks } from './publications-links.mjs';

import logicOfSacrificeEn from '../assets/publications/logic-of-sacrifice-en.jpg';
import logicOfSacrificeEs from '../assets/publications/logic-of-sacrifice-es.jpg';
import scienceCatchUpEn from '../assets/publications/science-catch-up-en.jpg';
import scienceCatchUpEs from '../assets/publications/science-catch-up-es.jpg';

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
  /** arXiv identifier, e.g. 'arXiv:2307.11414'. Preprints only. */
  arxivId?: string;
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
    arxivId: 'arXiv:2607.14169',
    doi: 'https://doi.org/10.48550/arXiv.2607.14169',
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
    arxivId: 'arXiv:2307.11414',
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
    ...(item.arxivId ? { identifier: item.arxivId } : {}),
    ...(item.doi ? { sameAs: item.doi } : {}),
    ...(item.kind === 'thesis' ? { inSupportOf: 'PhD in Mathematics' } : {}),
  }));

  return [...bookSchemas, ...researchSchemas];
}
