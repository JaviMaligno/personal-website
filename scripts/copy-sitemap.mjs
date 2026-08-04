// Some crawlers and older links expect /sitemap.xml, but @astrojs/sitemap emits
// sitemap-0.xml + sitemap-index.xml. This copies the first one into place.
//
// The location moved when the Vercel adapter was added: a purely static build
// writes to dist/, an adapted one writes to dist/client/ and Vercel then copies
// that into .vercel/output/static. Cover every location that exists so the
// build works with and without the adapter.
import { existsSync, copyFileSync } from 'node:fs';
import { join } from 'node:path';

const candidates = ['dist', join('dist', 'client'), join('.vercel', 'output', 'static')];

let copied = 0;
for (const dir of candidates) {
  const source = join(dir, 'sitemap-0.xml');
  if (existsSync(source)) {
    copyFileSync(source, join(dir, 'sitemap.xml'));
    console.log(`sitemap.xml written in ${dir}`);
    copied += 1;
  }
}

if (copied === 0) {
  console.error('postbuild: no sitemap-0.xml found in ' + candidates.join(', '));
  process.exit(1);
}
