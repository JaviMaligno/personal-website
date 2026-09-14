# Publish checklist — "Count the Rings or Sear the Squid"

Artículo del paper de los calamares. **Programado para 2026-09-22** en
`.github/publish-schedule.json` (entrada en `main` desde el 2026-09-14), rama
`blog/count-the-rings`, ya empujada a origin.

Su compañero, **`proved-certified-swept-sampled`**, está escrito y programado
para **2026-09-24** en la rama `blog/proved-certified-swept-sampled`, también
empujada. Todo lo de este documento aplica a los dos salvo donde se diga.

## Bloqueantes — el artículo NO puede publicarse sin esto

### 1. El ID de arXiv

El envío es `submit/8077477` (2026-09-14, primary math.MG), y a fecha de
escritura seguía en `submitted`, pendiente de moderación y anuncio. Los dos
ficheros del artículo y el hilo de X llevan el marcador `XXXX.XXXXX`.

Cuando arXiv anuncie, sustituirlo en:

- `src/content/blog/en/count-the-rings.md` (cuerpo y `linkedinLinks`)
- `src/content/blog/es/count-the-rings.md` (cuerpo y `linkedinLinks`)
- `docs/marketing/x-thread-count-the-rings.md` (tuit 12)

Y anotarlo en `docs/arxiv-envio.md` del repo `calamares`, donde hay una casilla
esperándolo, y añadir el paper a `src/data/publications.ts`.

La entrada del manifiesto debe llevar `blockIfMatches: "XXXX\\.XXXXX"`, así que
mientras el marcador siga ahí el workflow se niega a publicar y abre issue. Es
la única red de seguridad automática que tiene este artículo.

### 2. La v2 del preprint — **decisión de Javier**

La sección *"What the edge looks like outside the frying pan"* / *"Qué aspecto
tiene el filo fuera de la sartén"* cuenta resultados que **no están en la v1
publicada**: la generalización a contenedor arbitrario y cualquier dimensión
(G1–G7) y los del cuadrado (contraejemplo con `rho = 337/200`, gemelas en
cuadrado, `tau_cuadrado <= Y ~ 1.684487745872346`).

A 2026-09-14 ese material estaba **sin commitear** en el repo `calamares`
(`docs/drafts/generalizacion_dimensional.md`, `cuadrado_certificado.md`,
`cuadrado_gemelas.md`, `cuadrado_limite.md` y sus scripts y tests), escrito y
comprobado pero sin revisión adversaria independiente.

El artículo lo etiqueta explícitamente como no público y sin revisar. Aun así,
antes del 22 hay que elegir una de dos:

- **Subir la v2** (o al menos publicar esas notas en el repo público, que el
  artículo enlaza), de modo que el lector pueda comprobar lo que lee; o
- **Quitar esa sección** del artículo en los dos idiomas y guardarla para
  cuando la v2 exista. Es una sección autocontenida: se corta entera sin tocar
  el resto, y el único arreglo pendiente sería el tuit 11 del hilo, que también
  se cae.

Javier se encarga de esta decisión.

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
