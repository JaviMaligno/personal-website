import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const slug = 'when-ai-chooses-the-questions';
const colors = { bg:'#1a1a24', text:'#e2e8f0', muted:'#94a3b8', teal:'#2dd4bf', amber:'#fbbf24' };
const labels = {
  en: { title:'Three different questions', rows:[['Correctness','Does the conclusion follow?','A proof checked against','its definitions and assumptions.'],['Understanding','Can I use the idea?','Adapt the argument, identify limits,','recognize a new application.'],['Judgment','Is this worth studying?','Explain the priority and assess','what the work makes possible.']], chartTitle:'New submissions to arXiv', sub:'All disciplines · January–August each year', foot:'Submission volume does not measure understanding', note:'and does not isolate the effect of AI.' },
  es: { title:'Tres preguntas diferentes', rows:[['Corrección','¿Se sigue la conclusión?','Una prueba contrastada con','sus definiciones e hipótesis.'],['Comprensión','¿Puedo usar la idea?','Adaptar el argumento, ver límites,','reconocer una aplicación nueva.'],['Criterio','¿Merece la pena estudiarlo?','Justificar la prioridad y valorar','qué permite hacer el trabajo.']], chartTitle:'Nuevos envíos a arXiv', sub:'Todas las disciplinas · enero–agosto de cada año', foot:'El volumen de envíos no mide la comprensión', note:'ni aísla el efecto de la IA.' }
};
const svgStart=(height)=>`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="${height*2}" viewBox="0 0 600 ${height}"><rect width="600" height="${height}" rx="16" fill="${colors.bg}"/><g font-family="Arial, Helvetica, sans-serif">`;
const text=(x,y,value,size=16,fill=colors.text,extra='')=>`<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" ${extra}>${value}</text>`;
const csv = await fs.readFile(path.join(root, 'docs/research/ai-mathematical-taste/arxiv-monthly-submissions-2026-09-21.csv'), 'utf8');
const months = csv.trim().split(/\r?\n/).slice(1).map(line => {
  const [month, submissions] = line.split(',');
  return { month, submissions: Number(submissions) };
});
const years = [2022, 2023, 2024, 2025, 2026];
const values = years.map(year => {
  const period = months.filter(row => row.month.startsWith(year + '-') && Number(row.month.slice(-2)) <= 8);
  if (period.length !== 8 || period.some(row => !Number.isFinite(row.submissions))) throw new Error('Incomplete January–August data for ' + year);
  return period.reduce((sum, row) => sum + row.submissions, 0);
});
for (const lang of ['en','es']) {
  const l=labels[lang];
  let comparison=svgStart(406)+text(26,39,l.title,23,colors.text,'font-weight="700"');
  l.rows.forEach((row,i)=>{const y=66+i*108; const accent=i===2?colors.amber:colors.teal;
    comparison+=`<rect x="22" y="${y}" width="556" height="96" rx="9" fill="#232332"/><rect x="22" y="${y}" width="4" height="96" rx="2" fill="${accent}"/>`;
    comparison+=text(39,y+30,row[0],21,accent,'font-weight="700"')+text(39,y+60,row[1],15)+text(305,y+39,row[2],14,colors.muted)+text(305,y+62,row[3],14,colors.muted);
  });
  comparison+='</g></svg>';
  let chart=svgStart(485)+text(28,37,l.chartTitle,23,colors.text,'font-weight="700"')+text(28,63,l.sub,14,colors.muted);
  const left=76, top=108, plotWidth=425, max=250000;
  [0,50000,100000,150000,200000,250000].forEach(value=>{const x=left+value/max*plotWidth;chart+=`<line x1="${x}" y1="88" x2="${x}" y2="382" stroke="#363647"/>`+text(x,405,value===0?'0':(value/1000)+'k',13,colors.muted,'text-anchor="middle"');});
  values.forEach((value,i)=>{const y=top+i*55;const width=value/max*plotWidth;chart+=text(25,y+21,String(years[i]),16)+`<rect x="${left}" y="${y}" width="${width}" height="29" rx="4" fill="${i===4?colors.amber:colors.teal}"/>`+text(left+width+8,y+20,value.toLocaleString(lang==='es'?'es-ES':'en-US'),14);});
  chart+=text(28,443,l.foot,15,colors.muted)+text(28,465,l.note,15,colors.muted)+'</g></svg>';
  for (const [name,svg] of [['criteria',comparison],['arxiv',chart]]) {
    const output=path.join(root,'public/blog',slug+'-'+name+'-'+lang+'.png');
    await sharp(Buffer.from(svg)).png().toFile(output);
    console.log(output);
  }
}
