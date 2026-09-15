# Publish checklist — "Count the Rings or Sear the Squid"

Artículo del paper de los calamares. **Programado para 2026-09-22** en
`.github/publish-schedule.json` (entrada en `main` desde el 2026-09-14), rama
`blog/count-the-rings`, ya empujada a origin.

Su compañero, **`proved-certified-swept-sampled`**, está escrito y programado
para **2026-09-24** en la rama `blog/proved-certified-swept-sampled`, también
empujada. Todo lo de este documento aplica a los dos salvo donde se diga.

## Bloqueantes — el artículo NO puede publicarse sin esto

### 1. ~~El ID de arXiv~~ — RESUELTO el 2026-09-15

El preprint salió anunciado como
**[`arXiv:2609.15554`](https://arxiv.org/abs/2609.15554)** (DOI
`10.48550/arXiv.2609.15554`). Verificado contra la página de arXiv: título,
autor, primaria math.MG y cross-lists cs.CG y math.CO coinciden con el envío.

El marcador `XXXX.XXXXX` está sustituido en los seis sitios — cuerpo y
`linkedinLinks` de los cuatro ficheros de artículo, y los dos hilos de X, cuya
nota de cabecera ya no pide sustituir nada. Ambas ramas empujadas. Los dos
preprints (este y el de paper 3, `arXiv:2608.28541`) están en
`src/data/publications.ts` con sus resúmenes en los dos idiomas, y el ID queda
anotado en `docs/arxiv-envio.md` del repo `calamares`.

Las entradas del manifiesto conservan su `blockIfMatches` a propósito: ya no
dispara, y si alguien reintrodujera el marcador volvería a proteger.

### 2. ~~La v2 del preprint~~ — RESUELTO el 2026-09-15

La v2 está **enviada**: `submit/8082585`, un reemplazo de `2609.15554`, en
estado `submitted` a la espera de moderación y anuncio. Compilada por arXiv sin
errores, 73 páginas.

Con ella, lo que los artículos citaban como "escrito pero no público" pasa a ser
parte del preprint, y además cambia un resultado central: **la igualdad
$	au = arphi$ está demostrada**, vía el criterio de los tres mayores. Los dos
artículos ya están actualizados en consecuencia:

- `count-the-rings`: la sección del umbral ya no dice que la cota inferior sea
  conjetural, e incorpora el teorema de los tres mayores; la sección del filo
  pierde el aviso de "no público" y gana los cinco aros en toda dimensión, las
  gemelas cuadradas con la cota `Y`, y los agujeros independientes con la
  garantía de área `min(1, kappa^-2 - 1)` y su umbral `1/raíz(2)`. El hilo de X
  pasa a trece tuits.
- `proved-certified-swept-sampled`: anota que el lema del quinteto pertenece al
  programa de casos especializados que el teorema global ya no necesita como
  premisa, y que el certificado sigue siendo correcto aunque ya no sostenga nada.

**Único cabo pendiente**: si arXiv anuncia la v2 *después* del 22, los artículos
citarán `arXiv:2609.15554` — que es correcto, porque el identificador no cambia
— pero el lector que entre ese día verá la v1. No rompe nada y no bloquea la
publicación.

## Ya hecho

- EN y ES escritos, mismo `translationKey`, `pubDate` 2026-09-22, build verde y
  ambas páginas generadas.
- `linkedinSummary` escrito a mano en los dos idiomas, así que Gemini no se
  llama para este post. `repoUrl` apunta al repo del paper.
- Siete figuras, una por ejemplo trabajado, generadas por
  `docs/marketing/hero-sources/count-the-rings-figures.py` en los dos idiomas,
  con las posiciones calculadas y aserciones que fallan si la geometría deja de
  ser exacta. Hero determinista en `count-the-rings.py`, 1020x510 verificado.
- Fórmulas en LaTeX (KaTeX ya estaba configurado en el proyecto). **Ojo:**
  `$$…$$` en una sola línea NO renderiza; hay que abrir y cerrar en líneas
  propias.
- Hilo de X de 12 tuits, todos verificados bajo 280 caracteres.

## Pendiente, no bloqueante

- ~~Entrada del calendario~~ y ~~push de las ramas~~: hechos el 2026-09-14.
  Para empujar hizo falta `gh auth switch --user JaviMaligno`; la cuenta activa
  era la de la empresa y el push pedía contraseña.
- ~~Choque de fechas el 21~~: resuelto moviendo `that-was-for-another-chat` al
  23 (fecha del manifiesto **y** `pubDate` de sus dos ficheros, que también
  decía 21). La semana queda 21 → 22 → 23 → 24, un artículo por día.
- **El selector no se puede ejecutar a mano en Windows**: la última línea de
  `scripts/publish/select-due-article.mjs` compara `import.meta.url` con
  `process.argv[1]`, que aquí son `file:///C:/…` y `C:\…`, así que `main()`
  nunca corre y el script sale en silencio con código 0. En Actions (Linux)
  funciona. Para validar en local, importar `validateManifest` y
  `selectDueArticle` desde otro script.
- Dos ejemplos citados sin figura: el contraejemplo cuadrado y el ejemplo que
  distingue 2D de 3D. Faltan las coordenadas del testigo completo en las notas;
  con ellas se dibujan igual que los demás.
