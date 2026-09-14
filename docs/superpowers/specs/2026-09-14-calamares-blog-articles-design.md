# Diseño — Dos artículos y dos hilos para el paper de los calamares

**Fecha:** 2026-09-14. **Estado:** aprobado en conversación, pendiente de plan.

El paper: *Greedy Packing of Nested Rings: Placement Rules, a Golden
Counterexample, and a Tribonacci Floor* (Javier Aguilar Martín). Enviado a
arXiv el 2026-09-14, `submit/8077477`, primaria math.MG, cross-lists cs.CG y
math.CO, 60 páginas. Repo público `github.com/JaviMaligno/calamares`, release
`v1-arxiv`. **El ID de arXiv no existe aún**: el envío está en `submitted`,
pendiente de moderación y anuncio.

Dos artículos, cortados **por audiencia** y no por profundidad (a diferencia
del par del paper 3, que era el mismo hilo largo y corto). Cada uno se lee sin
el otro.

---

## Artículo 1 — el matemático

**Slug:** `count-the-rings`.
**Título EN (trabajo):** *Count the Rings or Sear the Squid*.
**Título ES (trabajo):** *Contar aros no es freír calamares*.
**Extensión:** 2.500–3.500 palabras. **Sin moraleja de software**: se sostiene
como matemáticas.

### Arco

1. **La sartén.** Echas aros de calamar. Dos objetivos razonables: que quepan
   cuantos más mejor, o que se dore la mayor superficie posible. Un aro
   pequeño cabe en el agujero de uno mayor, así que hay decisiones reales.
   Contexto: es pariente del *Recursive Circle Packing Problem* (Pedroso,
   Cunha y Tavares 2016; resuelto exactamente por Gleixner, Maher, Müller y
   Pedroso 2020), que modela el telescopaje de tubos en contenedores. Esa
   literatura es algorítmica y heurística; aquí las preguntas son
   estructurales.

2. **Resultado A — divergen de verdad.** El área de contacto se comporta como
   `2πw·Σrᵢ` menos una penalización `πw²` por aro; la cardinalidad cuenta aros.
   *Divergencia* = el óptimo de área tiene estrictamente menos aros que el
   máximo de cardinalidad.
   - **Dos aros nunca divergen** (si ambos caben, el conjunto completo es
     óptimo para los dos; si no, todo conjunto factible tiene a lo sumo uno).
   - **Tres ya pueden**: `R = 10`, `w = 9/2`, radios `{8, 101/20, 99/20}`
     (racional-exacto, script `divergencia3`, 5/5). El par pequeño es
     exactamente diametral (`101/20 + 99/20 = 10`), nada coexiste ni anida con
     el 8 (su agujero tiene radio `7/2 < 99/20`), y las áreas comparan
     `a(8) = 207π/4 > 198π/4 = a(101/20) + a(99/20)`: el área prefiere el
     aro único, la cardinalidad prefiere el par. Mecanismo: superaditividad
     pura a grosor grande, donde ningún agujero permite anidar y el problema
     degenera a empaquetamiento de círculos.
   - **El mecanismo del agujero necesita cuatro**: `R = 10`, `w = 1`, radios
     `{9.0, 4.2, 4.2, 4.2}`. Óptimo de área: el 9.0 con un 4.2 anidado
     (`N = 2`, `A ≈ 76.7`). Óptimo de cardinalidad: los tres 4.2 (`N = 3`,
     `A ≈ 69.7`). Más aros, menos calamar dorado. **Esta es la imagen central
     del artículo.**
   - **Diagrama de fases** para la familia "un aro grande `b` más aros
     pequeños iguales de radio `s`" a `w = 1`, `R = 10` (script `franja`):
     una escalera gobernada por los umbrales óptimos probados de n círculos
     iguales en un disco, con borde superior exactamente el umbral de tres
     círculos, `0.4641R`.
   - **Honestidad de etiqueta**: el inicio de la divergencia de tres aros
     cerca de `w/R ≈ 0.26` es **barrido, no umbral probado**. Decirlo en la
     misma frase que lo enuncia, como hace el paper.

3. **Resultado B — y sin embargo.** Condición sobre los tamaños:
   **superincreciente** = cada radio mayor que la suma de todos los menores.
   Bajo ella, el voraz descendente no optimiza *un* objetivo: computa el
   conjunto factible lexicográficamente máximo y por tanto maximiza
   `Σ v(rᵢ)` **para toda `v` positiva, estrictamente creciente y
   superaditiva** a la vez — el área de contacto entre ellas. Los dos
   objetivos dejan de divergir.
   Y además: **da igual dónde coloques cada aro.** Cualquier elección entre
   contenedores factibles da el mismo resultado. El teorema está enunciado y
   probado para **contenedor arbitrario en `ℝ^d`** (`main.tex:306`, `:351`):
   la prueba solo usa clausura hacia abajo de los empaquetamientos, el lema de
   fila aplicado dentro de la bola vaciada, y la cota de radio total; nada
   mira la forma ni la dimensión. Cubre *verbatim* planchas rectangulares y
   tubos/cascarones esféricos en 3D — el escenario original del RCPP.
   Corroboración computacional: 100 instancias superincrecientes aleatorias,
   best-fit, worst-fit y colocación aleatoria dieron resultados óptimos (y por
   tanto idénticos) sin excepción.

4. **El filo.** Un párrafo por pieza, tono de anécdota, sin montar secciones:
   - La irrelevancia de colocación vale incondicionalmente hasta **tres** aros
     y **falla en cuatro**.
   - Las **instancias gemelas** descartan toda regla de colocación que sea
     función del estado observable.
   - Se mide cuánto te sales con `ρ = maxᵢ (Σ_{j>i} r_j)/rᵢ`. El modelo
     aditivo tiene umbral universal exactamente `ρ = 1`.
   - En el geométrico, la familia rígida de cuatro aros tiene ínfimo
     exactamente la constante de Tribonacci `T ≈ 1.83929`, probado sin
     idealización de tangencia. Pero `T` **no** es el umbral global: una
     familia áurea explícita (sartén `φ+1`, radios
     `{φ, 1, φ/2+2ε, φ/2+ε}`) rompe la irrelevancia en `ρ = φ+3ε` para todo
     `ε > 0` pequeño, lo que **prueba `τ ≤ φ < T`** y refuta la conjetura
     natural del umbral de Tribonacci. La cota `τ ≥ φ` sigue conjetural
     (probada para perfiles de pares y fuera de una región pesada explícita).
   - **Acotar explícitamente**: todo el afilado es **específico del disco**.
     Sus análogos en cuadrado y en `ℝ³` están abiertos. No presumir de
     generalidad aquí; la generalidad está en la mitad positiva.

5. **Cierre.** "¿Qué estoy maximizando de verdad?" no es filosofía: decide la
   respuesta. Y existen regímenes donde la pregunta difícil desaparece del
   todo — conviene saber si estás en uno.

### Figuras

Reusar las del paper, que ya existen:
- `figures/divergencia_calamares.png` — la instancia mínima, óptimo de área
  frente a óptimo de cardinalidad.
- `figures/franja_divergencia.png` — el diagrama de fases.

---

## Artículo 2 — el gradiente de certeza

**Slug:** `proved-certified-swept-sampled`.
**Título EN (trabajo):** *Proved, Certified, Swept, Sampled*.
**Título ES (trabajo):** *Probado, certificado, barrido, muestreado*.
**Extensión:** 2.500–3.000 palabras.

**Restricción vinculante de contenido:** este artículo existe porque tiene
**razonamiento matemático propio**, distinto del artículo 1 (que va de
estructura y umbrales; este va del filo de la tangencia y de la aritmética
exacta). No es "cómo escribí un paper con IA" — eso ya está publicado en
*Writing a Research Paper with AI* (2026-07-21) y repetirlo sería el mismo
artículo con otro decorado. Si al escribirlo la sustancia matemática no
aguanta, **el artículo se cae** y queda solo el artículo 1; no se rellena con
proceso.

Los calamares aparecen solo como escenario: no se explica la matemática del
empaquetamiento.

### Arco

1. **El problema.** Sesenta páginas donde conviven pruebas escritas a mano,
   teoremas comprobados por el kernel de Lean (57), barridos de cajas con
   aritmética exacta y muestreo. Todo se imprime con la misma cara. No valen
   lo mismo y el lector no tiene forma de saber sobre cuál apoyarse.

2. **La propuesta — cuatro etiquetas.** Cada afirmación lleva su etiqueta
   epistémica: `proved`, `box-certified`, `grid-swept`, `sampled`
   (`main.tex:95`), y un mapa de verificación empareja cada afirmación
   computacional con el script que la respalda. No es verificado/no
   verificado: es un gradiente declarado. Ejemplo interno: el suelo de
   Tribonacci es `proved`; el inicio de divergencia en `w/R ≈ 0.26` va marcado
   como barrido en la misma frase.

3. **Por qué hace falta — `quintetocert` v1→v4.** Cuatro certificados del
   quinteto `j = 1` (`thm:gapwritten`), tres refutados por revisión
   adversarial:
   - **v1** cae por mallas sin Lipschitz, LP con tolerancias y `R₃ ≤ M`
     muestreado.
   - **v2**, racional-dirigido, refutado **en el filo**: una tolerancia de
     `1e-12` engrosaba la variedad tangente justo en el punto áureo. En
     `(Σ, α, o₁) = (φ, φ, φ)` la configuración es tangente exacta, así que la
     tolerancia convierte "toca justo" en "cabe con holgura". El certificado
     daba verde precisamente donde la pregunta era delicada. **Este es el
     corazón del artículo.**
   - **v3** incorpora el teorema del trío aportado por el propio refutador:
     `{α, o₁, m}` cabe en `R_used` en todo el dominio, con `b₂` diametral
     creciente y `b₂(2, √5−1) = 1` — la identidad del *mirror corner*,
     kernel-checked en Lean.
   - **v4** cierra sin ninguna hipótesis numérica: `asin` certificado por
     serie racional pura (`sin²` y `cos` encajonados en ℚ con resto de
     Lagrange alternante), toda suma/resta en intervalos con redondeo dirigido
     (`nextafter` tras cada operación), `π` y `2π` certificados en ℚ por la
     misma serie (gate A9), y `math.asin` usado como **oráculo no creído**,
     con bracket propio que solo avanza con certeza direccional. Resultado:
     4/4, 11.973 cajas, dominio entero, cero tolerancias, cero exclusiones.
   - **La reparación es una prueba, no un parche.** El corner doble
     `(s' = φ/2, w* = 1/φ)` resulta **fantasma**: la tercera ligadura
     `w* ≤ Σ − 2s'` lo vacía. El corner real no cabe en disposición mural
     porque el arco inferior suma `π + 1.4e-4`. El testigo correcto **apila**
     `w*` radialmente bajo `s'`, y en el punto áureo todo sale en identidades
     exactas en ℚ[√5]: `s'_ext = 1/2`, `d_w = 2φ − 1 − 1/φ = φ`, y margen
     `dist² − (w* + α)² = 1/φ³`.

4. **La otra mitad de la honestidad.** Tramos donde el barrido no termina y se
   declaran **agotados por coste** (millones de cajas, presupuestos de
   segundos excedidos) en lugar de fingir cobertura completa. Una afirmación
   etiquetada como declaración honesta vale más que una etiquetada como
   probada sin serlo. Mencionar también el diseño de la ronda ciega: siete
   referees por bloque más un meta, con `docs/` **prohibido** para que no
   heredaran las hipótesis del autor; 0 hallazgos fatales, 61 correcciones.

5. **Traducción.** Tus tests, tus tipos, tus pruebas de propiedad y tus
   comprobaciones a mano son cuatro etiquetas distintas, y el CI las pinta
   todas del mismo verde. La pregunta no es "¿está verificado?" sino "¿con qué
   etiqueta — y dónde deja de valer?".

---

## Calendario y publicación

| Fecha | Artículo | Rama |
|---|---|---|
| martes 2026-09-22 | 1 — `count-the-rings` | `blog/count-the-rings` |
| jueves 2026-09-24 | 2 — `proved-certified-swept-sampled` | `blog/proved-certified-swept-sampled` |

Comprobado a 2026-09-14:
- La cola de `.github/publish-schedule.json` llega sin huecos hasta 2026-09-20,
  y hasta el 21 cuando entre `blog/pegado-accidental`
  (`that-was-for-another-chat`). El 22 es el primer día libre.
- `scripts/linkedin/posts/schedule.json` no tiene ningún post suelto después
  de 2026-09-03, así que ninguna de las dos fechas duplica post de LinkedIn.

**Dónde vive la entrada del manifiesto.** En `main`, **no** en la rama del
artículo: es el patrón real del repo — `being-wrong-can-be-free`,
`the-bug-nobody-can-reach` y `the-memory-that-was-true` no tocan
`publish-schedule.json`. Así no hay conflicto entre ramas ni hace falta driver
de merge (y `union` sobre un JSON produciría un fichero inválido).

**No pueden publicarse los dos el mismo día.** `selectDueArticle`
(`scripts/publish/select-due-article.mjs`) corta en seco si `main` ya lleva una
publicación de hoy, filtra por `date <= today`, ordena y devuelve **una sola**
entrada (`due[0]`, la más antigua primero para drenar atrasos).

**Guarda del ID de arXiv.** Ambas entradas llevan
`blockIfMatches: "XXXX\\.XXXXX"` con su `blockReason`. Los dos artículos citan
el preprint (cuerpo y `linkedinLinks`), y el ID no existirá hasta el anuncio.
Si el marcador sigue sin sustituir el día que vence, el workflow se niega a
publicar y abre issue; se recupera solo en la siguiente salida del cron en
cuanto se ponga el ID real. Es imposible que salga un enlace a
`arxiv.org/abs/XXXX.XXXXX`.

---

## Entregables

Por artículo:
- `src/content/blog/en/<slug>.md` y `src/content/blog/es/<slug>.md`, mismo
  `translationKey`, `pubDate` igual a la fecha del manifiesto, frontmatter
  validado contra el esquema de la colección.
- `linkedinSummary` escrito a mano y fijado en el frontmatter EN (evita la
  llamada a Gemini), y `linkedinLinks` con el preprint.
- Hero 1020×510 exacto en `public/blog/<slug>.png`, con fuente determinista en
  `docs/marketing/hero-sources/<slug>.py` y entrada en
  `docs/marketing/image-prompts.md` (ese fichero tiene driver `union`, así que
  las dos ramas pueden añadir su bloque sin conflicto).
- Hilo de X en `docs/marketing/x-thread-<slug>.md`: cada tuit en su propio
  bloque de código, verificado bajo 280 caracteres, el primero suelto y cada
  siguiente como respuesta al anterior. No hay automatización de X: se publica
  a mano, y el workflow abre la issue recordatoria porque el fichero existe.
  - Hilo 1 (~9 tuits): ancla en la instancia mínima con la figura — tres aros,
    o dos y más calamar dorado. Cierra con preprint y artículo.
  - Hilo 2 (~11 tuits): ancla en la tolerancia de `1e-12` que daba verde justo
    en el punto áureo. Cierra con las cuatro etiquetas.

Una vez:
- `src/data/publications.ts`: añadir **calamares** (cuando haya ID) y también
  el **paper 3** (`arXiv:2608.28541`, *An Enclosed Mode Is a Gauge Choice*),
  ya anunciado (envío del 2026-08-28) y que sigue sin aparecer en la lista.
- Las dos entradas de `.github/publish-schedule.json`, commiteadas en `main`.

## Fuera de alcance

- Generalización dimensional del paper: anotada en
  `docs/generalizaciones.md` §1 del repo `calamares` (commit `0c3f4b4`), se
  retoma aparte.
- Cualquier reescritura de artículos ya publicados.
- Automatizar la publicación en X.
