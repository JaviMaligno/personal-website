import './deny-io.cjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
const local = createRequire(import.meta.url);
const [{ createMarkdownProcessor }, { default: remarkMath }, { default: rehypeKatex }, { default: katex }] = await Promise.all([
  import('@astrojs/markdown-remark'), import('remark-math'), import('rehype-katex'), import('katex'),
]);
assert.equal(katex.version, '0.18.10');
const processor = await createMarkdownProcessor({ syntaxHighlight: false, remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] });
for (const filename of ['src/content/blog/es/count-the-rings.md', 'src/content/blog/en/verified-world-model-still-loses.md']) {
  const { code } = await processor.render(fs.readFileSync(path.join(root, filename), 'utf8'));
  assert.ok(code.includes('<annotation encoding="application/x-tex">'), filename);
  assert.ok(!code.includes('katex-error'), filename);
  assert.ok(code.includes('katex-mathml') && code.includes('katex-html'));
}
const cssPath = local.resolve('katex/dist/katex.min.css');
const css = fs.readFileSync(cssPath, 'utf8');
for (const selector of ['.katex-mathml', '.katex-display', '.katex-base']) assert.ok(css.includes(selector));
const fonts = [...css.matchAll(/url\(([^)]+)\)/g)].map(match => match[1].replace(/['"]/g, ''));
assert.ok(fonts.length > 0);
for (const font of fonts) {
  assert.match(font, /^fonts\/KaTeX_[\w-]+\.(?:woff2?|ttf)$/);
  assert.ok(fs.statSync(path.join(path.dirname(cssPath), font)).isFile());
}
const layout = fs.readFileSync(path.join(root, 'src/layouts/BlogLayout.astro'), 'utf8');
assert.ok(layout.includes('import "katex/dist/katex.min.css"'));
assert.ok(!layout.includes('cdn.jsdelivr.net/npm/katex@'));
const routing = local('@vercel/routing-utils');
const config = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
assert.match(fs.readFileSync(path.join(root, 'astro.config.mjs'), 'utf8'), /trailingSlash:\s*'always'/);
const output = routing.getTransformedRoutes({ ...config, trailingSlash: true });
assert.equal(output.error, null);
const before = JSON.parse(fs.readFileSync(new URL('./routing-baseline.json', import.meta.url), 'utf8'));
const publicPatterns = ['redirects', 'rewrites', 'headers'].flatMap(kind => (config[kind] || []).map(route => ({ kind, source: route.source, compiled: routing.sourceToRegex(route.source) })));
const transformed = output.routes.map(route => ({ ...route, matches: route.src ? before.samples.map(sample => ({ sample, captures: new RegExp(route.src).exec(sample)?.slice(1).map(value => value ?? null) ?? null })) : [] }));
assert.deepEqual(publicPatterns, before.publicPatterns);
assert.deepEqual(transformed, before.transformed, 'Actual site routing order, redirects, headers, destinations and captures preserved');
assert.deepEqual(globalThis.__offlineDependencyAttempts, { network: 0, processes: 0, envReads: 0 });
console.log(`PASS: two real articles, local KaTeX CSS/${fonts.length} font references and actual site routing`);
