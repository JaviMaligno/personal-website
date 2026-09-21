// Raster counterparts for the article's inline figures (Dev.to cannot render SVG).
// Run from any directory: node scripts/figures/frontend-backend-agentic-core.mjs
import { readFile } from 'node:fs/promises';
import sharp from 'sharp';

const root = new URL('../../', import.meta.url);
const slug = 'frontend-backend-agentic-core';
const article = await readFile(new URL(`src/content/blog/en/${slug}.md`, root), 'utf8');
const figures = [...article.matchAll(/<figure class="fab-fig">([\s\S]*?)<\/figure>/g)];
if (!figures.length) throw new Error('No figures found');

for (const [index, figure] of figures.entries()) {
  const svg = figure[1].match(/<svg[\s\S]*?<\/svg>/)?.[0];
  if (!svg) throw new Error(`Figure ${index + 1} has no SVG`);
  const standalone = svg.replace('<svg ', '<svg font-family="Arial, sans-serif" ');
  const output = new URL(`public/blog/${slug}-fig-${index + 1}.png`, root);
  await sharp(Buffer.from(standalone), { density: 144 })
    .flatten({ background: '#1a1a24' })
    .png()
    .toFile(output.pathname);
  console.log(output.pathname);
}
