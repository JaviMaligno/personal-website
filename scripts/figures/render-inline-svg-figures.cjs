const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [md, slug, outdir] = process.argv.slice(2);
  const src = fs.readFileSync(md, 'utf8');
  const figs = [...src.matchAll(/<figure class="[a-z0-9-]*fig">([\s\S]*?)<\/figure>/g)].map(m => m[1]);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 800 }, deviceScaleFactor: 1 });
  for (let i = 0; i < figs.length; i++) {
    const svg = figs[i].match(/<svg[\s\S]*?<\/svg>/)[0];
    await p.setContent(`<html><body style="margin:0;background:#1a1a24"><div style="padding:40px 50px;"><div style="font-family:Inter,system-ui,sans-serif">${svg.replace('<svg ', '<svg style="display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif" ')}</div></div></body></html>`);
    const el = await p.$('body > div');
    await el.screenshot({ path: `${outdir}/${slug}-fig-${i + 1}.png` });
  }
  console.log(figs.length);
  await b.close();
})();
