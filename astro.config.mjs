// @ts-check
import { defineConfig } from 'astro/config';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

import sitemap from '@astrojs/sitemap';
import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
  site: 'https://www.javieraguilar.ai',

  // The site stays static — every page is still prerendered. The adapter is
  // here only so a single endpoint (src/pages/api/assessment.ts) can run on
  // demand, which it opts into with `export const prerender = false`.
  adapter: vercel(),

  markdown: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [rehypeKatex],
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