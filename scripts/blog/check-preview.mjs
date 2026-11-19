#!/usr/bin/env node
// Visual review of a blog article on a deployed Vercel preview (or production).
//
//   node scripts/blog/check-preview.mjs <base-url> <slug> [--out <dir>]
//
// Opens /en/blog/<slug>/ and /es/blog/<slug>/, takes full-page screenshots at
// 1440, 1180 and 390 px, prints their paths and runs the render checks that
// have caught real defects before (page-level horizontal scroll, squashed
// table cells, KaTeX errors, broken inline SVG, unrendered math). It also
// lists literal mentions of other posts' titles that are not links.
// Exit 1 when any check fails. Read the screenshots anyway: the checks only
// cover the defects that have a mechanical signature.
//
// Preview deployments sit behind Vercel's login. If
// ~/.config/vercel/personal-website-bypass exists, its content is sent as the
// x-vercel-protection-bypass header (with x-vercel-set-bypass-cookie, so the
// page's own sub-requests carry the bypass cookie).
//
// Playwright is not a dependency of this repo: it is imported from the global
// npm install (override with PLAYWRIGHT_PATH). This machine does not run
// `npm run dev` or builds; review against what Vercel deployed.

import { existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const WIDTHS = [1440, 1180, 390];
const LANGS = ['en', 'es'];
const MIN_CELL_WIDTH = 60;
const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const BYPASS_FILE = join(homedir(), '.config', 'vercel', 'personal-website-bypass');
const DEFAULT_PLAYWRIGHT = 'C:/Users/Usuario/AppData/Roaming/npm/node_modules/playwright/index.mjs';

function usage(msg) {
  if (msg) console.error(msg);
  console.error('Usage: node scripts/blog/check-preview.mjs <base-url> <slug> [--out <dir>]');
  process.exit(2);
}

function parseArgs(argv) {
  const positional = [];
  let out = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') out = argv[++i];
    else if (argv[i].startsWith('--out=')) out = argv[i].slice(6);
    else positional.push(argv[i]);
  }
  if (positional.length !== 2) usage();
  const [base, slug] = positional;
  if (!/^https?:\/\//.test(base)) usage(`Base URL must start with http(s)://: ${base}`);
  return { base: base.replace(/\/+$/, ''), slug: slug.replace(/^\/+|\/+$/g, ''), out };
}

function defaultOutDir(slug) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const root = process.env.TEMP || process.env.TMP || tmpdir();
  return join(root, 'claude', 'blog-preview', `${slug}-${stamp}`);
}

function loadTitles(lang, slug) {
  const dir = join(REPO_ROOT, 'src', 'content', 'blog', lang);
  if (!existsSync(dir)) return [];
  const titles = [];
  for (const file of readdirSync(dir)) {
    if (!file.endsWith('.md') || file === `${slug}.md`) continue;
    const text = readFileSync(join(dir, file), 'utf8');
    const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!fm) continue;
    const line = fm[1].match(/^title:\s*(.+)$/m);
    if (!line) continue;
    let title = line[1].trim();
    if (/^(["']).*\1$/.test(title)) title = title.slice(1, -1);
    title = title.replace(/\\"/g, '"').replace(/''/g, "'");
    // One-word titles match too much ordinary prose; skip them.
    if (title.split(/\s+/).length < 2) continue;
    titles.push({ slug: file.replace(/\.md$/, ''), title });
  }
  return titles;
}

function readBypass() {
  if (!existsSync(BYPASS_FILE)) return null;
  const token = readFileSync(BYPASS_FILE, 'utf8').trim();
  return token || null;
}

// Runs in the page. Returns { problems: [], warnings: [] }.
function pageChecks({ minCellWidth }) {
  const problems = [];
  const warnings = [];
  const root = document.querySelector('.article-content') || document.querySelector('article') || document.querySelector('main') || document.body;
  const vw = document.documentElement.clientWidth;
  const describe = (el) => {
    const cls = typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 50);
    return `<${el.tagName.toLowerCase()}${cls}>${text ? ` "${text}"` : ''}`;
  };
  const clipsX = (el) => {
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      const o = getComputedStyle(a).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return a;
    }
    return null;
  };

  // 1. Page-level horizontal scroll.
  const sw = document.documentElement.scrollWidth;
  if (sw > vw + 1) {
    const offenders = [];
    for (const el of document.body.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width && r.right > vw + 1 && !clipsX(el)) offenders.push(`${describe(el)} right=${Math.round(r.right)}`);
      if (offenders.length >= 5) break;
    }
    problems.push(`horizontal page scroll: scrollWidth ${sw} > viewport ${vw}. ${offenders.join('; ')}`);
  }
  // Tables that scroll inside their own box: legitimate on mobile, suspicious on desktop.
  for (const table of root.querySelectorAll('table')) {
    const box = clipsX(table) || table;
    if (box.scrollWidth > box.clientWidth + 1) {
      warnings.push(`table scrolls horizontally inside its box (${box.scrollWidth} > ${box.clientWidth}): ${describe(table)}`);
    }
  }

  // 2. Narrow table cells with their text broken over several lines.
  for (const cell of root.querySelectorAll('td, th')) {
    const text = (cell.textContent || '').trim();
    if (!text) continue;
    const r = cell.getBoundingClientRect();
    if (r.width >= minCellWidth) continue;
    const range = document.createRange();
    range.selectNodeContents(cell);
    const tops = new Set([...range.getClientRects()].filter((q) => q.width > 0).map((q) => Math.round(q.top)));
    if (tops.size > 1) problems.push(`table cell ${Math.round(r.width)}px wide with text split over ${tops.size} lines: ${describe(cell)}`);
  }

  // 3. KaTeX errors.
  for (const el of root.querySelectorAll('.katex-error')) problems.push(`KaTeX error: ${describe(el)} ${el.getAttribute('title') || ''}`.trim());

  // 4. Broken inline SVG: SVG elements parsed outside an <svg>, or SVG markup shown as text.
  const stray = [...root.querySelectorAll('text, tspan, rect, path, line, circle, polyline, polygon, g, defs, marker')].filter((el) => !el.closest('svg'));
  if (stray.length) problems.push(`${stray.length} SVG element(s) outside an <svg> (a blank line inside the <figure> ends the HTML block): ${stray.slice(0, 3).map(describe).join('; ')}`);

  // Text-node walk for literal markup and unrendered math.
  const skip = 'script, style, svg, code, pre, kbd, samp, .katex, .katex-display, math, textarea';
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.parentElement && !n.parentElement.closest(skip) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  const svgText = /<\/?(svg|text|tspan|rect|path|g|line|circle|polyline|polygon|figure)\b[^>]*>/i;
  const mathPatterns = [
    { re: /(^|[\s(])[A-Za-zα-ωΑ-Ω](?:_\{?\w+\}?)?\s*(?:[<>≤≥]=?|=|≠)\s*-?(?:\d[\d.,]*|[A-Za-z](?![A-Za-z]))/, what: 'comparison' },
    { re: /\$[^$\s][^$]{0,80}\$/, what: 'unrendered $…$' },
    { re: /\\(frac|sum|prod|int|alpha|beta|gamma|lambda|sigma|cdot|times|leq?|geq?|neq|approx|mathbb|mathrm|text)\b/, what: 'LaTeX command' },
  ];
  const seen = new Set();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n.nodeValue;
    if (!t || !t.trim()) continue;
    if (svgText.test(t)) problems.push(`SVG/HTML markup shown as text: "${t.trim().slice(0, 80)}"`);
    for (const { re, what } of mathPatterns) {
      const m = t.match(re);
      if (!m) continue;
      const key = what + m[0];
      if (seen.has(key)) continue;
      seen.add(key);
      problems.push(`math outside KaTeX (${what}): "${m[0].trim()}" in "${t.trim().slice(0, 80)}"`);
    }
  }
  return { problems, warnings };
}

// Runs in the page. Returns the titles mentioned literally outside an <a>.
function unlinkedTitles({ titles }) {
  const root = document.querySelector('.article-content') || document.querySelector('article') || document.querySelector('main') || document.body;
  const norm = (s) => s.toLowerCase().replace(/[‘’´`]/g, "'").replace(/[“”«»]/g, '"').replace(/\s+/g, ' ');
  const chunks = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.parentElement && !n.parentElement.closest('a, script, style, svg, code, pre') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  for (let n = walker.nextNode(); n; n = walker.nextNode()) chunks.push(n.nodeValue);
  // Join with a space so a title split across inline elements (<em>, <strong>) still matches.
  const text = norm(chunks.join(' '));
  return titles.filter(({ title }) => text.includes(norm(title)));
}

async function main() {
  const { base, slug, out } = parseArgs(process.argv.slice(2));
  const outDir = resolve(out || defaultOutDir(slug));
  mkdirSync(outDir, { recursive: true });

  const pwPath = process.env.PLAYWRIGHT_PATH || DEFAULT_PLAYWRIGHT;
  let chromium;
  try {
    ({ chromium } = await import(pathToFileURL(pwPath).href));
  } catch (err) {
    console.error(`Cannot load Playwright from ${pwPath} (set PLAYWRIGHT_PATH): ${err.message}`);
    process.exit(2);
  }

  const bypass = readBypass();
  if (!bypass) {
    console.warn(`WARN: ${BYPASS_FILE} not found; a protected Vercel preview will answer with its login page.`);
  }
  const origin = new URL(base).origin;

  // The global Playwright's bundled Chromium may be missing (browsers belong to
  // another Playwright version); fall back to the installed Chrome.
  let browser;
  try {
    browser = await chromium.launch();
  } catch {
    browser = await chromium.launch({ channel: 'chrome' });
  }
  const problems = [];
  const warnings = [];
  const shots = [];
  const mentions = [];
  try {
    for (const lang of LANGS) {
      const url = `${base}/${lang}/blog/${slug}/`;
      const titles = loadTitles(lang, slug);
      for (const width of WIDTHS) {
        const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
        if (bypass) {
          // Only to the preview's own origin: sending it to font or CDN hosts can break CORS.
          await context.route('**/*', (route) => {
            const req = route.request();
            if (new URL(req.url()).origin !== origin) return route.continue();
            return route.continue({ headers: { ...req.headers(), 'x-vercel-protection-bypass': bypass, 'x-vercel-set-bypass-cookie': 'true' } });
          });
        }
        const page = await context.newPage();
        const tag = `${lang} ${width}px`;
        let res;
        try {
          res = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
        } catch (err) {
          problems.push(`[${tag}] cannot load ${url}: ${err.message.split('\n')[0]}`);
          await context.close();
          continue;
        }
        const finalUrl = page.url();
        if (new URL(finalUrl).origin !== origin || (res && [401, 403].includes(res.status()))) {
          problems.push(`[${tag}] Vercel login wall (landed on ${finalUrl}, HTTP ${res?.status()}): ${bypass ? 'the bypass token was rejected' : 'create the bypass token'}`);
          await context.close();
          break;
        }
        if (res && res.status() >= 400) {
          problems.push(`[${tag}] HTTP ${res.status()} for ${url}`);
          await context.close();
          break;
        }
        // Lazy images and client-side diagrams: scroll to the end and back, then let them settle.
        await page.evaluate(async () => {
          for (let y = 0; y < document.body.scrollHeight; y += 800) {
            window.scrollTo(0, y);
            await new Promise((r) => setTimeout(r, 60));
          }
          window.scrollTo(0, 0);
          await document.fonts.ready;
        });
        await page.waitForLoadState('networkidle').catch(() => {});

        const file = join(outDir, `${slug}-${lang}-${width}.png`);
        await page.screenshot({ path: file, fullPage: true });
        shots.push(file);

        const r = await page.evaluate(pageChecks, { minCellWidth: MIN_CELL_WIDTH });
        problems.push(...r.problems.map((p) => `[${tag}] ${p}`));
        warnings.push(...r.warnings.map((w) => `[${tag}] ${w}`));
        if (width === WIDTHS[0]) {
          const found = await page.evaluate(unlinkedTitles, { titles });
          mentions.push(...found.map((f) => `[${lang}] "${f.title}" -> /${lang}/blog/${f.slug}/`));
        }
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`Screenshots (${outDir}):`);
  for (const s of shots) console.log(`  ${s}`);
  console.log(`\nUnlinked mentions of other posts' titles: ${mentions.length ? '' : 'none'}`);
  for (const m of mentions) console.log(`  ${m}`);
  if (warnings.length) {
    console.log(`\nWarnings (${warnings.length}):`);
    for (const w of warnings) console.log(`  ${w}`);
  }
  if (problems.length) {
    console.log(`\nProblems (${problems.length}):`);
    for (const p of problems) console.log(`  ${p}`);
    process.exit(1);
  }
  console.log('\nNo mechanical problems found. Read the screenshots before handing over.');
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});
