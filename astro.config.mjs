// @ts-check
import { defineConfig } from 'astro/config';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeTableWrap from './src/plugins/rehype-table-wrap.mjs';

import sitemap from '@astrojs/sitemap';
import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
  site: 'https://www.javieraguilar.ai',

  // Every page is canonically the version with the trailing slash, and until
  // now the version without one answered 200 as well. Search Console shows
  // what that cost: the same article indexed twice, and several of the
  // slashless variants sitting in "Crawled - currently not indexed". This
  // makes Vercel redirect them instead of serving a second copy.
  trailingSlash: 'always',

  // The site stays static — every page is still prerendered. The adapter is
  // here only so a single endpoint (src/pages/api/assessment.ts) can run on
  // demand, which it opts into with `export const prerender = false`.
  adapter: vercel(),

  markdown: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [rehypeKatex, rehypeTableWrap],
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es'],
    routing: {
      prefixDefaultLocale: true,
      redirectToDefaultLocale: false
    }
  },

  integrations: [
    sitemap({
      filter: (page) => page !== 'https://www.javieraguilar.ai/',
    })
  ]
});