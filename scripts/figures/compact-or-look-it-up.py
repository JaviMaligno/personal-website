"""Figuras de `compact-or-look-it-up`: una celda por episodio.

Datos de github.com/JaviMaligno/delayed-relevance, rama exp/compaction-vs-transcript:
results/compaction/{A-haiku55,C-haiku55,C-haiku55-coh}/reporte.txt (columna «1er dep.»
en C, «metrica» en A) y results/bloque1-coherente/*.json (caja del primer dependiente).
Escribe los SVG en stdout separados por una línea `=====`, para pegarlos en EN y ES.

Uso: python scripts/figures/compact-or-look-it-up.py en|es
"""
import sys

TEAL, AMBER, MUTED, TEXT, SLATE = "#2dd4bf", "#f59e0b", "#94a3b8", "#e2e8f0", "#64748b"
MONO = "ui-monospace,'JetBrains Mono',monospace"

ES = len(sys.argv) > 1 and sys.argv[1] == "es"


def t(en, es):
    return es if ES else en


def celdas(x, y, ok, mal, nulo=0, tam=14, hueco=4):
    out = []
    for i in range(ok + mal + nulo):
        cx = x + i * (tam + hueco)
        if i < ok:
            out.append(f'<rect x="{cx}" y="{y}" width="{tam}" height="{tam}" rx="2" fill="{TEAL}"/>')
        elif i < ok + mal:
            out.append(f'<rect x="{cx + 1}" y="{y + 1}" width="{tam - 2}" height="{tam - 2}" rx="2" '
                       f'fill="none" stroke="{AMBER}" stroke-width="2"/>')
        else:
            out.append(f'<rect x="{cx + 4}" y="{y + 4}" width="{tam - 8}" height="{tam - 8}" rx="1" '
                       f'fill="{SLATE}"/>')
    return "".join(out)


def leyenda(y, con_nulo=False):
    s = (f'<rect x="150" y="{y}" width="12" height="12" rx="2" fill="{TEAL}"/>'
         f'<text x="168" y="{y + 10}" class="m">{t("applied / correct", "aplicada / acierta")}</text>'
         f'<rect x="321" y="{y + 1}" width="10" height="10" rx="2" fill="none" stroke="{AMBER}" stroke-width="2"/>'
         f'<text x="338" y="{y + 10}" class="m">{t("missed", "falla")}</text>')
    if con_nulo:
        s += (f'<rect x="414" y="{y + 4}" width="6" height="6" fill="{SLATE}"/>'
              f'<text x="426" y="{y + 10}" class="m">{t("no decisive step", "sin paso decisivo")}</text>')
    return s


def svg(alto, label, cuerpo):
    return (f'<svg viewBox="0 0 600 {alto}" role="img" aria-label="{label}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<style>.t{{font:13px {MONO};fill:{TEXT}}}.m{{font:12px system-ui,sans-serif;fill:{MUTED}}}'
            f'.h{{font:600 13px system-ui,sans-serif;fill:{TEXT}}}</style>{cuerpo}</svg>')


BRAZOS = ["react", "summary", "hybrid_lookup", "summary_lookup", "fresh_lookup", "skillstate"]

# Figura 1: sonda A (detalle a 40 pasos), Haiku 5.5. (aciertos, fallos, sin paso decisivo)
A = {"react": (10, 2, 0), "summary": (9, 1, 2), "hybrid_lookup": (12, 0, 0),
     "summary_lookup": (11, 0, 1), "fresh_lookup": (3, 5, 4), "skillstate": (1, 11, 0)}
cuerpo = f'<text x="20" y="28" class="h">{t("A detail read 40 steps earlier, two compactions in between", "Un detalle leído 40 pasos antes, con dos compactaciones de por medio")}</text>'
for i, b in enumerate(BRAZOS):
    y = 52 + i * 26
    cuerpo += f'<text x="140" y="{y + 11}" class="t" text-anchor="end">{b}</text>'
    cuerpo += celdas(150, y, *A[b])
    ok, mal, _ = A[b]
    cuerpo += f'<text x="{150 + 12 * 18 + 8}" y="{y + 11}" class="m">{ok}/{ok + mal}</text>'
cuerpo += leyenda(52 + 6 * 26 + 10, True)
fig1 = svg(240, t("Probe A, Haiku 5.5: the summary keeps the detail (9 of 10) as well as the full transcript (10 of 12); the fresh session that searches gets 3 of 8.",
                  "Sonda A, Haiku 5.5: el resumen conserva el detalle (9 de 10) igual que el transcript completo (10 de 12); la sesión limpia que consulta acierta 3 de 8."), cuerpo)

# Figura 2: sonda C, Haiku 5.5, primer paso decisivo por episodio, aviso viejo vs coherente.
VIEJO = {"react": 4, "summary": 2, "hybrid_lookup": 1, "summary_lookup": 2, "fresh_lookup": 0, "skillstate": 2}
COH = {"react": 5, "summary": 6, "hybrid_lookup": 6, "summary_lookup": 5, "fresh_lookup": 2, "skillstate": 5}
cuerpo = (f'<text x="150" y="28" class="h">{t("Notice contradicts history", "El aviso contradice la historia")}</text>'
          f'<text x="380" y="28" class="h">{t("Coherent notice", "Aviso coherente")}</text>')
for i, b in enumerate(BRAZOS):
    y = 46 + i * 26
    cuerpo += f'<text x="140" y="{y + 11}" class="t" text-anchor="end">{b}</text>'
    cuerpo += celdas(150, y, VIEJO[b], 6 - VIEJO[b])
    cuerpo += f'<text x="262" y="{y + 11}" class="m">{VIEJO[b]}/6</text>'
    cuerpo += celdas(380, y, COH[b], 6 - COH[b])
    cuerpo += f'<text x="492" y="{y + 11}" class="m">{COH[b]}/6</text>'
cuerpo += leyenda(46 + 6 * 26 + 10)
fig2 = svg(234, t("Probe C, Haiku 5.5, decisive step per episode: with a notice that contradicts the history most arms miss; with a coherent notice every arm but the fresh session applies it in 5 or 6 of 6.",
                  "Sonda C, Haiku 5.5, paso decisivo por episodio: con un aviso que contradice la historia casi todos los brazos fallan; con un aviso coherente todos menos la sesión limpia lo aplican en 5 o 6 de 6."), cuerpo)

# Figura 3: el bloque 1 repetido con Haiku 4.5, 12 episodios por celda.
R = {("skillstate", 0): 12, ("react", 0): 3, ("skillstate", 1): 12, ("react", 1): 10}
cuerpo = (f'<text x="150" y="28" class="h">{t("Notice contradicts history", "El aviso contradice la historia")}</text>'
          f'<text x="150" y="122" class="h">{t("Coherent notice", "Aviso coherente")}</text>')
for c in (0, 1):
    for j, b in enumerate(("skillstate", "react")):
        y = 44 + c * 94 + j * 28
        etiqueta = "explicit state" if b == "skillstate" else "full transcript"
        if ES:
            etiqueta = "estado explícito" if b == "skillstate" else "transcript completo"
        cuerpo += f'<text x="140" y="{y + 11}" class="t" text-anchor="end">{etiqueta}</text>'
        cuerpo += celdas(150, y, R[(b, c)], 12 - R[(b, c)])
        cuerpo += f'<text x="{150 + 12 * 18 + 8}" y="{y + 11}" class="m">{R[(b, c)]}/12</text>'
cuerpo += leyenda(214)
fig3 = svg(240, t("The earlier replication rerun on Haiku 4.5: explicit state 12 of 12 against the full transcript 3 of 12 when the notice contradicts history; 12 of 12 against 10 of 12 when it does not.",
                  "La réplica anterior repetida con Haiku 4.5: estado explícito 12 de 12 frente a transcript completo 3 de 12 cuando el aviso contradice la historia; 12 de 12 frente a 10 de 12 cuando no."), cuerpo)

print(fig1, fig2, fig3, sep="\n=====\n")
