const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [md, slug, outdir, heroHtml] = process.argv.slice(2);
  const src = fs.readFileSync(md, 'utf8');
  const figs = [...src.matchAll(/<figure class="[a-z0-9-]*fig">([\s\S]*?)<\/figure>/g)].map(m => m[1]);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 800 }, deviceScaleFactor: 1 });
  for (let i = 0; i < figs.length; i++) {
    const m = figs[i].match(/<svg[\s\S]*?<\/svg>/);
    const out = `${outdir}/${slug}-fig-${i + 1}.png`;
    if (!m) { fs.copyFileSync(`${outdir}/${slug}-prime-sum.png`, out); continue; }
    await p.setContent(`<html><body style="margin:0;background:#1a1a24"><div style="padding:40px 50px;"><div style="font-family:Inter,system-ui,sans-serif">${m[0].replace('<svg ', '<svg style="display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif" ')}</div></div></body></html>`);
    await (await p.$('body > div')).screenshot({ path: out });
  }
  if (heroHtml) {
    const h = await b.newPage({ viewport: { width: 1020, height: 510 }, deviceScaleFactor: 2 });
    await h.setContent(fs.readFileSync(heroHtml, 'utf8'));
    await h.screenshot({ path: `${outdir}/${slug}.png` });
  }
  console.log(figs.length);
  await b.close();
})();
