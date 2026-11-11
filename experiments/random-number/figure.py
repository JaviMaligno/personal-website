"""Build the article's random-number figure (inline SVG) from the measured results.

Humans: YouGov, GB adults, 12-13 Sep 2024, n=2241, open question "Think of a
random number from 1-10" (totals column of the published table, in %).
AI: every results/*.json file, pooled; the per-model counts go in the README.

Usage: python figure.py <lang>   (prints the <figure> block)
"""
import json
import sys
from pathlib import Path

YOUGOV = [2, 4, 7, 9, 8, 14, 33, 14, 6, 4]

TEXT = {
    'es': {'h': 'Personas', 'ai': 'IA', 'u': 'Al azar', 'y': '% de respuestas',
           'aria': 'Distribución de los números elegidos al pedir uno al azar del 1 al 10. Al azar, cada número saldría un 10 % de las veces. Las personas eligen el 7 un {h7} % de las veces. Los modelos de IA medidos lo eligen un {a7} % de las veces.',
           'cap': 'Personas: encuesta de YouGov a {hn} adultos (septiembre de 2024). IA: {an} respuestas de {m} modelos de Claude y GPT a la misma pregunta. La línea discontinua es lo que saldría al azar.'},
    'en': {'h': 'People', 'ai': 'AI', 'u': 'Random', 'y': '% of answers',
           'aria': 'Distribution of the numbers chosen when asked for a random one from 1 to 10. At random, each number would come up 10% of the time. People choose 7 {h7}% of the time. The AI models measured choose it {a7}% of the time.',
           'cap': 'People: YouGov survey of {hn} adults (September 2024). AI: {an} answers from {m} Claude and GPT models to the same question. The dashed line is what chance would give.'},
}


def load_ai():
    counts, models = [0] * 10, 0
    for f in sorted(Path(__file__).with_name('results').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for k in range(10):
            counts[k] += d['counts'][str(k + 1)]
        models += 1
    return counts, models


def fmt(x, lang):
    s = f'{x:.0f}' if abs(x - round(x)) < 0.05 else f'{x:.1f}'
    return s.replace('.', ',') if lang == 'es' else s


def figure(lang):
    t = TEXT[lang]
    ai, nmodels = load_ai()
    total = sum(ai)
    aip = [100 * c / total for c in ai]
    X0, X1, Y0, Y1 = 64, 588, 30, 250  # plot box: y=Y1 is 0 %, y=Y0 is 100 %
    sy = lambda p: Y1 - (Y1 - Y0) * p / 100
    step = (X1 - X0) / 10
    out = [f'<svg viewBox="0 0 600 300" role="img" aria-label="{t["aria"].format(h7=YOUGOV[6], a7=fmt(aip[6], lang))}">']
    for p in (0, 25, 50, 75, 100):
        y = sy(p)
        out.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="rgba(255,255,255,0.08)"/>')
        out.append(f'<text x="{X0 - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#94a3b8" font-size="11">{p}</text>')
    out.append(f'<text x="14" y="{(Y0 + Y1) / 2:.0f}" fill="#94a3b8" font-size="11" transform="rotate(-90 14 {(Y0 + Y1) / 2:.0f})" text-anchor="middle">{t["y"]}</text>')
    bw = 16
    for k in range(10):
        cx = X0 + step * (k + 0.5)
        for p, dx, col in ((YOUGOV[k], -bw - 1, '#2dd4bf'), (aip[k], 1, '#f59e0b')):
            if p > 0:
                out.append(f'<rect x="{cx + dx:.1f}" y="{sy(p):.1f}" width="{bw}" height="{Y1 - sy(p):.1f}" rx="2" fill="{col}"/>')
        out.append(f'<text x="{cx:.1f}" y="{Y1 + 18}" text-anchor="middle" fill="#e2e8f0" font-size="12">{k + 1}</text>')
    cx7 = X0 + step * 6.5
    out.append(f'<text x="{cx7 - bw / 2 - 1:.1f}" y="{sy(YOUGOV[6]) - 6:.1f}" text-anchor="middle" fill="#5eead4" font-size="11" font-weight="700">{YOUGOV[6]}</text>')
    out.append(f'<text x="{cx7 + bw / 2 + 1:.1f}" y="{sy(aip[6]) - 6:.1f}" text-anchor="middle" fill="#fbbf24" font-size="11" font-weight="700">{fmt(aip[6], lang)}</text>')
    out.append(f'<line x1="{X0}" y1="{sy(10):.1f}" x2="{X1}" y2="{sy(10):.1f}" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>')
    # legend
    lx, ly = X0 + 16, Y0 + 14
    for i, (col, label, dash) in enumerate((('#2dd4bf', t['h'], False), ('#f59e0b', t['ai'], False), ('#e2e8f0', t['u'], True))):
        y = ly + i * 20
        if dash:
            out.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 14}" y2="{y - 4}" stroke="{col}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        else:
            out.append(f'<rect x="{lx}" y="{y - 10}" width="14" height="12" rx="2" fill="{col}"/>')
        out.append(f'<text x="{lx + 22}" y="{y}" fill="#e2e8f0" font-size="12">{label}</text>')
    out.append('</svg>')
    hn = '2.241' if lang == 'es' else '2,241'
    an = f'{total:,}'.replace(',', '.') if lang == 'es' else f'{total:,}'
    cap = t['cap'].format(hn=hn, an=an, m=nmodels)
    return '<figure class="wml-fig">\n' + '\n'.join(out) + f'\n<figcaption>{cap}</figcaption>\n</figure>'


if __name__ == '__main__':
    print(figure(sys.argv[1]))
