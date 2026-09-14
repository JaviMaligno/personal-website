# Artículo 1 del paper de los calamares — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar el 2026-09-22 el artículo divulgativo del paper de los calamares (EN + ES), con sus dos figuras, su hero, su hilo de X y su entrada de calendario.

**Architecture:** Rama `blog/count-the-rings` con todo el contenido; la entrada de `.github/publish-schedule.json` va aparte, en `main` (patrón del repo). El cron diario mergea la rama el día que vence y dispara blog, Dev.to y LinkedIn; el hilo de X se publica a mano.

**Tech Stack:** Astro 5 content collections (zod), matplotlib + PIL para el hero, markdown bilingüe con `translationKey`.

**Spec:** `docs/superpowers/specs/2026-09-14-calamares-blog-articles-design.md`. Este plan cubre **solo el artículo 1**. El artículo 2 (`proved-certified-swept-sampled`, 2026-09-24) tiene su propio plan, después del checkpoint humano.

**Fuente de los datos:** repo `C:\Users\Usuario\Github\calamares`, release `v1-arxiv`. Todos los números de abajo están ya verificados contra `paper/main.tex`; no hace falta volver a abrirlo salvo para citar literalmente.

---

## Task 1: Rama y artículo EN

**Files:**
- Create: `src/content/blog/en/count-the-rings.md`

- [ ] **Step 1: Crear la rama desde main actualizado**

```bash
rtk git fetch origin main
rtk git checkout -b blog/count-the-rings origin/main
```

- [ ] **Step 2: Escribir el artículo EN**

Frontmatter exacto (el esquema está en `src/content/config.ts`; `pubDate` debe coincidir con la fecha del manifiesto):

```yaml
---
title: "Count the Rings or Sear the Squid"
description: "Drop squid rings into a frying pan and two reasonable goals — fit as many as possible, or sear as much surface as possible — turn out to be different problems with different answers. Unless the sizes obey one condition, and then not only do they agree: where you put each ring stops mattering at all."
pubDate: 2026-09-22
tags: ["Mathematics", "Geometry", "Optimization", "Research"]
lang: en
translationKey: count-the-rings
heroImage: "/blog/count-the-rings.png"
repoUrl: https://github.com/JaviMaligno/calamares
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
---
```

El marcador `XXXX.XXXXX` es deliberado: el preprint aún no está anunciado y la guarda del manifiesto (Task 8) impide publicar mientras siga ahí.

Arco del cuerpo, en este orden y con estos datos exactos:

1. **La sartén.** Aros de calamar en una sartén; dos objetivos razonables: que quepan cuantos más mejor, o dorar la mayor superficie. Un aro pequeño cabe en el agujero de uno mayor, así que hay decisiones reales. Situarlo: es pariente del *Recursive Circle Packing Problem* (Pedroso, Cunha y Tavares 2016; resuelto exactamente por Gleixner, Maher, Müller y Pedroso 2020), que modela el telescopaje de tubos en contenedores de envío. Esa literatura es algorítmica y sus métodos son heurísticas; aquí las preguntas son estructurales.

2. **Los dos objetivos divergen.** El área de contacto se comporta como `2πw·Σrᵢ` menos una penalización `πw²` por aro; la cardinalidad cuenta aros. *Divergencia* = el óptimo de área tiene estrictamente menos aros que el máximo de cardinalidad.
   - Dos aros nunca divergen: si ambos caben, el conjunto completo es óptimo para los dos (el área crece estrictamente por inclusión); si no caben, todo conjunto factible tiene a lo sumo un aro, cardinalidad que el óptimo de área alcanza.
   - Tres ya pueden: `R = 10`, `w = 9/2`, radios `{8, 101/20, 99/20}` (racional-exacto, script `divergencia3`, 5/5). El par pequeño es exactamente diametral (`101/20 + 99/20 = 10`); nada coexiste ni anida con el 8 porque su agujero tiene radio `7/2 < 99/20`; y las áreas comparan `a(8) = 207π/4 > 198π/4 = a(101/20) + a(99/20)`. El área prefiere el aro único; la cardinalidad, el par. Mecanismo: superaditividad pura a grosor grande, donde ningún agujero permite anidar y el problema degenera a empaquetamiento de círculos.
   - El mecanismo del agujero necesita cuatro, y es la imagen central: `R = 10`, `w = 1`, radios `{9.0, 4.2, 4.2, 4.2}`. Óptimo de área: el 9.0 con un 4.2 anidado (`N = 2`, `A ≈ 76.7`). Óptimo de cardinalidad: los tres 4.2 (`N = 3`, `A ≈ 69.7`). Más aros, menos calamar dorado.
   - Diagrama de fases para la familia "un aro grande más aros pequeños iguales de radio `s`", a `w = 1`, `R = 10` (script `franja`): una escalera gobernada por los umbrales óptimos probados de n círculos iguales en un disco, cuyo borde superior es exactamente el umbral de tres círculos, `0.4641R`.
   - **Honestidad obligatoria:** el inicio de la divergencia de tres aros cerca de `w/R ≈ 0.26` es un valor **barrido, no un umbral probado**. Decirlo en la misma frase que lo enuncia.

3. **Y sin embargo.** Condición **superincreciente**: cada radio mayor que la suma de todos los menores. Bajo ella el voraz descendente computa el conjunto factible lexicográficamente máximo, y por tanto maximiza `Σ v(rᵢ)` para **toda** `v` positiva, estrictamente creciente y superaditiva a la vez — el área de contacto entre ellas. Los dos objetivos dejan de divergir.
   Y además la colocación es irrelevante: cualquier elección entre contenedores factibles da el mismo resultado. Enunciado y probado para **contenedor arbitrario en `ℝ^d`**; la prueba solo usa clausura hacia abajo de los empaquetamientos, el lema de fila aplicado dentro de la bola vaciada, y la cota de radio total — nada mira la forma ni la dimensión. Cubre *verbatim* planchas rectangulares y tubos o cascarones esféricos en 3D, el escenario original del RCPP. Corroboración: 100 instancias superincrecientes aleatorias; best-fit, worst-fit y colocación aleatoria dieron resultados óptimos, y por tanto idénticos, sin excepción.

4. **El filo** (un párrafo por pieza, tono de anécdota, sin secciones propias):
   - La irrelevancia de colocación vale incondicionalmente hasta **tres** aros y **falla en cuatro**.
   - Las **instancias gemelas** descartan toda regla de colocación que sea función del estado observable.
   - Se mide cuánto te sales de la condición con `ρ = maxᵢ (Σ_{j>i} r_j)/rᵢ`. El modelo aditivo tiene umbral universal exactamente `ρ = 1`.
   - En el modelo geométrico, la familia rígida de cuatro aros tiene ínfimo exactamente la constante de Tribonacci `T ≈ 1.83929`, probado sin idealización de tangencia. Pero `T` no es el umbral global: una familia áurea explícita — sartén de radio `φ+1`, radios `{φ, 1, φ/2+2ε, φ/2+ε}` — rompe la irrelevancia en `ρ = φ+3ε` para todo `ε > 0` pequeño. Eso prueba `τ ≤ φ < T` y refuta la conjetura natural del umbral de Tribonacci. La cota `τ ≥ φ` sigue conjetural: probada para perfiles de pares y fuera de una región pesada explícita.
   - **Acotación obligatoria:** todo el afilado es **específico del disco**; sus análogos en cuadrado y en `ℝ³` están abiertos. La generalidad vive en la mitad positiva, no aquí.

5. **Cierre.** "¿Qué estoy maximizando de verdad?" no es filosofía: decide la respuesta. Y hay regímenes donde la pregunta difícil desaparece del todo — conviene saber si estás en uno.

Restricciones de forma:
- 2.500–3.500 palabras.
- **Sin moraleja de software.** Se sostiene como matemáticas; no traducir a agentes, CI, ni ingeniería.
- Las dos figuras se insertan en el paso 2 (Task 2 las deja en su sitio).
- Enlazar el repo `https://github.com/JaviMaligno/calamares` y el preprint con el marcador.

- [ ] **Step 3: Validar el frontmatter compilando**

```bash
rtk npm run build
```

Expected: build sin errores. Si el frontmatter tuviera una clave desconocida o faltara `translationKey`, Astro falla con el error de zod de la colección `blog`.

- [ ] **Step 4: Commit**

```bash
rtk git add src/content/blog/en/count-the-rings.md
rtk git commit -m "Add the count-the-rings article (EN)"
```

---

## Task 2: Las dos figuras del paper

**Files:**
- Create: `public/blog/count-the-rings-divergence.png`
- Create: `public/blog/count-the-rings-phase.png`
- Modify: `src/content/blog/en/count-the-rings.md`

- [ ] **Step 1: Copiar las figuras del repo del paper**

```bash
cp /c/Users/Usuario/Github/calamares/figures/divergencia_calamares.png public/blog/count-the-rings-divergence.png
cp /c/Users/Usuario/Github/calamares/figures/franja_divergencia.png public/blog/count-the-rings-phase.png
```

- [ ] **Step 2: Comprobar que son legibles y no gigantes**

```bash
python -c "from PIL import Image; [print(f, Image.open(f).size, __import__('os').path.getsize(f)//1024, 'KB') for f in ['public/blog/count-the-rings-divergence.png','public/blog/count-the-rings-phase.png']]"
```

Expected: dos líneas con tamaño en píxeles y peso. Si alguna pasa de 400 KB, reducir con
`python -c "from PIL import Image; im=Image.open('RUTA'); im.save('RUTA', optimize=True)"`.

- [ ] **Step 3: Insertarlas en el artículo**

Convención del repo: markdown con alt descriptivo y largo (ver `src/content/blog/en/ciphers-edges-of-language.md:42`). La de divergencia va en el punto 2, justo tras la instancia de cuatro aros; la de fases, tras el párrafo de la escalera.

```markdown
![The minimal divergence instance: a pan of radius 10 with rings of width 1. On the left, the area optimum — the radius-9 ring with one 4.2 ring nested inside it, two rings and about 76.7 units of contact area. On the right, the cardinality optimum — three separate 4.2 rings, three rings but only about 69.7 units of area.](/blog/count-the-rings-divergence.png)
```

```markdown
![Phase diagram of the divergence band for one large ring plus equal small rings of radius s, at width 1 in a pan of radius 10. The band forms a staircase whose steps are the proved optimal thresholds for packing n equal circles in a disk; its upper edge is exactly the three-circle threshold, 0.4641 times the pan radius.](/blog/count-the-rings-phase.png)
```

- [ ] **Step 4: Comprobar que el build las resuelve**

```bash
rtk npm run build
```

Expected: build verde. Las rutas `/blog/...` se sirven desde `public/`, así que un nombre mal escrito no rompe el build — verificar además que los dos ficheros existen con `ls public/blog/count-the-rings-*.png`.

- [ ] **Step 5: Commit**

```bash
rtk git add public/blog/count-the-rings-divergence.png public/blog/count-the-rings-phase.png src/content/blog/en/count-the-rings.md
rtk git commit -m "Add the divergence and phase-diagram figures"
```

---

## Task 3: Hero determinista

**Files:**
- Create: `docs/marketing/hero-sources/count-the-rings.py`
- Create: `public/blog/count-the-rings.png`

- [ ] **Step 1: Escribir la fuente del hero**

Convención del repo (ver `docs/marketing/hero-sources/` en la rama `blog/being-wrong-can-be-free`): script de matplotlib que dibuja el contraste central del artículo en vez de ilustrarlo, guarda en `public/blog/<slug>.png` y **fija el tamaño exacto a 1020×510 con PIL al final**, porque matplotlib redondea el lienzo un píxel a la baja y los scrapers de OG no llevan bien el alpha:

```python
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG, edgecolor="none", dpi=100)

    from PIL import Image

    im = Image.open(OUT).convert("RGB").resize((1020, 510), Image.LANCZOS)
    im.save(OUT)
    print(f"wrote {OUT} ({im.size[0]}x{im.size[1]})")
```

Qué dibuja: la instancia mínima, las dos soluciones lado a lado a escala real (`R = 10`, `w = 1`), izquierda el óptimo de área (aro de 9.0 con un 4.2 anidado) y derecha el de cardinalidad (tres 4.2). Bajo cada una, su par de números: `2 rings · area 76.7` y `3 rings · area 69.7`. Nada de leyendas largas ni títulos de ejes.

- [ ] **Step 2: Generar el hero**

```bash
python docs/marketing/hero-sources/count-the-rings.py
```

Expected: `wrote public/blog/count-the-rings.png (1020x510)`.

- [ ] **Step 3: Verificar el contrato de tamaño**

```bash
python -c "from PIL import Image; im=Image.open('public/blog/count-the-rings.png'); assert im.size==(1020,510), im.size; assert im.mode=='RGB', im.mode; print('hero ok', im.size, im.mode)"
```

Expected: `hero ok (1020, 510) RGB`. Si falla la aserción, el script no está fijando el tamaño con PIL.

- [ ] **Step 4: Mirar la imagen antes de darla por buena**

Abrir `public/blog/count-the-rings.png` y comprobar que los dos paneles se distinguen, que los números se leen a tamaño de tarjeta de LinkedIn y que no hay texto cortado.

- [ ] **Step 5: Commit**

```bash
rtk git add docs/marketing/hero-sources/count-the-rings.py public/blog/count-the-rings.png
rtk git commit -m "Add hero image for count-the-rings"
```

---

## Task 4: Entrada en image-prompts.md

**Files:**
- Modify: `docs/marketing/image-prompts.md`

- [ ] **Step 1: Añadir el bloque al final del fichero**

Este fichero tiene driver `merge=union` en `.gitattributes` precisamente para que cada rama añada su bloque al final sin conflicto. Añadir una sección con el título del artículo, la ruta de la fuente determinista (`docs/marketing/hero-sources/count-the-rings.py`) y, en un bloque ```text, un prompt de respaldo de `image_gen` por si hubiera que regenerarlo sin matplotlib: 1020×510, escena concreta de dos sartenes vistas desde arriba, izquierda un aro grande con otro pequeño dentro, derecha tres aros pequeños sueltos; texto permitido exactamente y solo `2 rings`, `3 rings`, `more area`, `less area`; sin logos, sin personas, sin gradientes morados.

- [ ] **Step 2: Commit**

```bash
rtk git add docs/marketing/image-prompts.md
rtk git commit -m "Record the hero prompt for count-the-rings"
```

---

## Task 5: Versión ES

**Files:**
- Create: `src/content/blog/es/count-the-rings.md`

- [ ] **Step 1: Escribir la versión española**

Mismo `translationKey: count-the-rings`, `lang: es`, mismo `pubDate: 2026-09-22`, mismo `heroImage`, mismo `repoUrl`, mismos `linkedinLinks` con el marcador `XXXX.XXXXX`. Título: `"Contar aros no es freír calamares"`.

No es traducción literal: es el mismo arco escrito en español, con los mismos números y las mismas dos acotaciones de honestidad (el `w/R ≈ 0.26` barrido y el afilado específico del disco). Los textos alternativos de las dos figuras van también en español.

- [ ] **Step 2: Verificar que las dos lenguas están emparejadas**

```bash
rtk npm run build
python -c "
import re,io
for L in ('en','es'):
    s=io.open(f'src/content/blog/{L}/count-the-rings.md',encoding='utf-8').read()
    print(L, re.search(r'translationKey:\s*(\S+)',s).group(1), re.search(r'pubDate:\s*(\S+)',s).group(1), re.search(r'heroImage:\s*(\S+)',s).group(1))
"
```

Expected: dos líneas idénticas salvo el prefijo `en`/`es`.

- [ ] **Step 3: Commit**

```bash
rtk git add src/content/blog/es/count-the-rings.md
rtk git commit -m "Add the count-the-rings article (ES)"
```

---

## Task 6: linkedinSummary a mano

**Files:**
- Modify: `src/content/blog/en/count-the-rings.md`
- Modify: `src/content/blog/es/count-the-rings.md`

- [ ] **Step 1: Escribir el cuerpo del post en el frontmatter EN**

Con `linkedinSummary` presente, `buildPostText` lo usa literal y **no llama a Gemini**; los enlaces, la línea de código y los hashtags se añaden solos, así que escribir solo el cuerpo. Contenido: la sartén, la instancia mínima con sus dos números (tres aros y 69.7 de área, o dos aros y 76.7), el giro de que bajo superincrecencia los dos objetivos coinciden y la colocación deja de importar en cualquier dimensión, y una pregunta final al lector sobre qué está optimizando de verdad. Sin jerga: `ρ`, Tribonacci y `τ ≤ φ` no entran aquí.

- [ ] **Step 2: Reflejar el mismo campo en el fichero ES**

Escribirlo en español (no traducir palabra por palabra) en el frontmatter de `src/content/blog/es/count-the-rings.md`.

- [ ] **Step 3: Verificar que el build sigue verde**

```bash
rtk npm run build
```

Expected: verde. `linkedinSummary` es un `z.string().optional()`, así que un bloque YAML mal indentado rompe aquí y no en producción.

- [ ] **Step 4: Commit**

```bash
rtk git add src/content/blog/en/count-the-rings.md src/content/blog/es/count-the-rings.md
rtk git commit -m "Pin the hand-written LinkedIn body for count-the-rings"
```

---

## Task 7: Hilo de X

**Files:**
- Create: `docs/marketing/x-thread-count-the-rings.md`

- [ ] **Step 1: Escribir el hilo**

Formato exacto del repo (ver `docs/marketing/x-thread-infer-the-rule-in-one-dimension.md`): título `# X thread — "Count the Rings or Sear the Squid"`, una nota de que no hay automatización de X y que hay que **sustituir el marcador `XXXX.XXXXX` antes de publicar**, y después cada tuit como `**N/**` seguido de su propio bloque de código triple-backtick, para que haya botón de copiar también en el móvil.

Nueve tuits, este recorrido:
1. Gancho: echas aros de calamar a la sartén y ya tienes un problema de optimización. Hilo.
2. Los dos objetivos: que quepan muchos, o que se dore mucha superficie. No son lo mismo.
3. La instancia mínima: sartén 10, grosor 1, aros 9.0, 4.2, 4.2, 4.2.
4. Tres aros sueltos: `N = 3`, área ≈ 69.7. El 9.0 con un 4.2 dentro: `N = 2`, área ≈ 76.7. Más aros, menos calamar hecho.
5. Con dos aros nunca pasa; con tres puede; el mecanismo del agujero necesita cuatro.
6. El giro: si cada aro es mayor que la suma de todos los menores, los dos objetivos coinciden y el voraz descendente los maximiza a la vez.
7. Y más: da igual dónde pongas cada aro. Cualquier colocación factible da lo mismo — contenedor de cualquier forma, en cualquier dimensión.
8. El filo: eso vale hasta tres aros y se rompe en cuatro; y el umbral que parecía gobernarlo (Tribonacci) no es el que manda — una familia áurea lo rompe antes.
9. Cierre con enlace al artículo y al preprint.

- [ ] **Step 2: Verificar que ningún tuit pasa de 280 caracteres**

```bash
python -c "
import io,re
s=io.open('docs/marketing/x-thread-count-the-rings.md',encoding='utf-8').read()
bloques=re.findall(r'\`\`\`\n(.*?)\`\`\`', s, re.S)
print('tuits:', len(bloques))
malos=[(i+1,len(b.rstrip())) for i,b in enumerate(bloques) if len(b.rstrip())>280]
print('pasados de 280:', malos or 'ninguno')
assert not malos
"
```

Expected: `tuits: 9` y `pasados de 280: ninguno`.

- [ ] **Step 3: Commit**

```bash
rtk git add docs/marketing/x-thread-count-the-rings.md
rtk git commit -m "Draft the X thread for count-the-rings"
```

---

## Task 8: Entrada del calendario (en main, no en la rama)

**Files:**
- Modify: `.github/publish-schedule.json` (en `main`)

- [ ] **Step 1: Empujar la rama del artículo**

```bash
rtk git push -u origin blog/count-the-rings
```

Antes de empujar, comprobar la cuenta activa: este repo es personal, así que `gh auth status` debe mostrar `JaviMaligno`. Si no, `gh auth switch --user JaviMaligno`.

- [ ] **Step 2: Añadir la entrada en main**

```bash
rtk git checkout main
rtk git pull
```

Añadir al final del array `articles` de `.github/publish-schedule.json`:

```json
    {
      "slug": "count-the-rings",
      "branch": "blog/count-the-rings",
      "article": "src/content/blog/en/count-the-rings.md",
      "date": "2026-09-22",
      "blockIfMatches": "XXXX\\.XXXXX",
      "blockReason": "El articulo cita el preprint de los calamares y aun lleva el marcador XXXX.XXXXX en vez del ID de arXiv (envio submit/8077477, pendiente de anuncio). Publicarlo dejaria enlaces a arxiv.org/abs/XXXX.XXXXX. Sustituye el marcador en la rama, en los dos idiomas y en el hilo de X, y relanza."
    }
```

- [ ] **Step 3: Validar el manifiesto con el propio selector**

```bash
node scripts/publish/select-due-article.mjs --slug count-the-rings
```

Expected: `A publicar: count-the-rings desde blog/count-the-rings`.

Se usa `--slug` y no `--today` a propósito: `isPublished` mira si el fichero existe en el árbol de trabajo, así que un `--today 2026-09-22` ejecutado hoy elegiría el artículo pendiente más antiguo (el del 15), no este. Con `--slug` se salta la fecha y se comprueba justo lo que interesa: que la entrada existe, está bien formada y apunta a una rama y un fichero correctos. Si cualquier entrada del manifiesto estuviera mal formada, `validateManifest` sale con código 2 y lo dice aquí, no el día de la publicación.

El script solo escribe en `$GITHUB_OUTPUT` si esa variable existe, así que fuera de Actions se limita a imprimir por pantalla.

- [ ] **Step 4: Commit y push**

```bash
rtk git add .github/publish-schedule.json
rtk git commit -m "Schedule count-the-rings for 2026-09-22"
rtk git push
```

---

## Task 9: Paper 3 en la página de publicaciones

**Files:**
- Modify: `src/data/publications.ts`

Independiente del artículo, pero pendiente desde agosto: el paper 3 está anunciado y no aparece en la lista. El de calamares **no** entra todavía: no tiene ID.

- [ ] **Step 1: Añadir la entrada al principio del array `research`**

El array está ordenado del más reciente al más antiguo, así que va antes de `omitted-mode-rare-rule`:

```typescript
  {
    slug: 'enclosed-mode-gauge-choice',
    key: 'enclosedMode',
    kind: 'preprint',
    title: 'An Enclosed Mode Is a Gauge Choice',
    authors: ['Javier Aguilar Martín'],
    venue: 'arXiv (cs.LG, cs.AI)',
    year: 2026,
    url: 'https://arxiv.org/abs/2608.28541',
    arxivId: 'arXiv:2608.28541',
    doi: 'https://doi.org/10.48550/arXiv.2608.28541',
    relatedArticle: 'being-wrong-can-be-free',
  },
```

- [ ] **Step 2: Comprobar si `key` necesita traducciones**

```bash
rtk grep -n "omittedMode" src/i18n/en.json src/i18n/es.json
```

Si `omittedMode` aparece ahí, añadir las entradas equivalentes para `enclosedMode` en los dos ficheros, con el mismo juego de claves. Si no aparece, no hay nada que añadir.

- [ ] **Step 3: Verificar el build**

```bash
rtk npm run build
```

Expected: verde. `relatedArticle: 'being-wrong-can-be-free'` apunta a un artículo que se publica el 15, antes que esto, así que el enlace resuelve.

- [ ] **Step 4: Commit y push**

```bash
rtk git add src/data/publications.ts src/i18n/en.json src/i18n/es.json
rtk git commit -m "List the paper 3 preprint on the publications page"
rtk git push
```

---

## Cuando arXiv anuncie el preprint

No es una tarea de este plan porque depende de un evento externo, pero es el único cabo suelto:

1. Sustituir `XXXX.XXXXX` por el ID real en `src/content/blog/en/count-the-rings.md`, `src/content/blog/es/count-the-rings.md` y `docs/marketing/x-thread-count-the-rings.md`, en la rama `blog/count-the-rings`.
2. Añadir el paper de calamares a `src/data/publications.ts` igual que en Task 9.
3. Anotar el ID en `docs/arxiv-envio.md` del repo `calamares`, donde ya hay una casilla esperándolo.

Si el 22 llega sin ID, el workflow se niega a publicar, abre issue y lo reintenta solo en la siguiente salida del cron. No hay nada que rescatar a mano salvo el marcador.
