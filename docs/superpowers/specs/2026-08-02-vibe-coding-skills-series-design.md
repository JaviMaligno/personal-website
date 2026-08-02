# Design: "Qué necesitas saber para vibe-codear algo real" (serie de blog + activo de mentoría)

Date: 2026-08-02
Branch: `blog/vibe-coding-skills-core`
Status: approved in brainstorming (core + rampas; cuatro verbos N0–N3; nueve
bloques; dos líneas de flotación; un solo gráfico y dos tablas)

## Propósito y audiencia

Serie bilingüe (EN + ES) sobre **qué habilidades necesita hoy una persona para
construir software con agentes**, con la escala explícita de qué es
imprescindible y qué es mejora.

Audiencia primaria de la pieza 1: **el vibe coder** — alguien que ya construye
con agentes, con o sin background técnico. Escrita de forma que la audiencia
técnica habitual del blog la reenvíe: el ingeniero que hereda, contrata o teme
lo que un no técnico ha puesto en producción. Ese reenvío es el canal de
captación real, no la búsqueda orgánica.

Objetivo secundario declarado: alimentar una **oferta de mentoría** en
javieraguilar.ai (ver "Pendientes fuera de la serie").

## Arquitectura de la serie: un core + dos rampas

Un artículo por perfil se repetiría solo: los perfiles no difieren en el
destino, sino en el punto de partida y en el fallo característico. De ahí el
reparto:

1. **Pieza 1 — el core (esta).** Qué necesitas para vibe-codear algo real,
   vengas de donde vengas. Contiene la escala N0–N3, el gráfico y las tablas.
   Evergreen y citable; las otras dos piezas y la página de mentoría apuntan
   aquí.
2. **Pieza 2 — desde cero.** La rampa de quien no tiene background: miedo a la
   terminal, no saber qué se puede pedir, delegar sin poder verificar. Los
   semi-técnicos (WordPress, no-code, automatizaciones) son una variante del
   mismo perfil con menos huecos, no un perfil aparte.
3. **Pieza 3 — desde el oficio.** La rampa del técnico: delega demasiado poco,
   verifica a mano lo que debería verificar una máquina, y no conoce el harness.

**Alcance del plan de implementación que sigue a este spec: solo la pieza 1.**
Las piezas 2 y 3 tendrán su propio ciclo spec → plan → implementación.

La pieza 1 incluye **dos secciones cortas de perfil** (desde cero / desde el
oficio) que anuncian las siguientes piezas sin desarrollarlas: "más detalle en
próximos artículos".

**No habrá artículo de taxonomía de perfiles.** Una taxonomía sin nada
accionable es contenido vacío. En su lugar: **post recopilatorio de LinkedIn**
al cierre de la serie, que enlaza las tres piezas y la mentoría bajo la idea
"vengas de donde vengas, puedo ayudarte por aquí". Ese post es el que convierte.

## Tesis del core

> Tu nivel no mide lo que sabes hacer. Mide **cuánto puedes soltar sin quedarte
> ciego.**

Cada peldaño habilita a delegar más, no a teclear más. Eso convierte la tabla en
un medidor de delegación en vez de un temario.

Hermano directo del artículo ya publicado
[`how-much-should-you-still-know`](../../../src/content/blog/en/how-much-should-you-still-know.md),
que mira el mismo problema desde el ingeniero que delega. Este lo mira desde
quien nunca fue ingeniero. Enlazar en ambos sentidos. La frase "no puedes
preguntar por un espacio cuya existencia desconoces" es el puente literal entre
los dos.

## La escala: cuatro verbos

La granularidad no es "cuánto sabes", es qué puedes hacer con ello:

- **N0 · Reconocer** — sabes que existe una categoría de cosa que puede salir
  mal. No sabes nombrarla. Efecto: no te pilla por sorpresa.
- **N1 · Conversar** — sabes formular la pregunta **y entender la respuesta**.
  La frontera con N0 no es la pregunta, es la comprensión de lo que te
  contestan. Incluye ejecutar un comando que el agente te dicta.
- **N2 · Comprobar** — lo verificas **tú, mirando el sistema**, sin fiarte de lo
  que te han contestado.
- **N3 · Decidir** — eliges entre opciones.

Regla de asignación, para que ninguna celda se cuele de nivel:

| Si la celda dice… | El nivel es |
|---|---|
| "sé que existe / que puede pasar" | N0 |
| "sé pedirlo, entiendo qué me contestan, ejecuto lo que me dictan" | N1 |
| "lo miro yo y confirmo que es cierto" | N2 |
| "elijo entre A y B" | N3 |

Todo vocabulario ("qué es una clave de cliente", "qué es el backend") es **N1**:
sirve para entender la respuesta, no para verificar nada. Toda elección técnica
(modelo, proveedor, tipo de base de datos, tipo de test, arquitectura) es **N3**
sin discusión.

## Las dos líneas de flotación

- **Fin de N1 — puedes construir algo que funcione.** Un juguete honesto.
- **Fin de N2 — puedes ponerlo delante de usuarios reales.** Aquí está la
  frontera demo/producción de verdad.
- **N3 — ya no necesitas mentoría.** Buena parte es material de la pieza 3.

Tres estados, no dos. Es lo que el lector usa para situarse.

## Los nueve bloques

### 1. Qué se puede pedir
Techo de todo lo demás; abre el artículo.
- **N0** un agente construye software entero, no solo escribe texto
- **N1** describir lo que quiero por resultado; pedirle que investigue y proponga
  antes de hacer; **entender la respuesta cuando dice que algo no se puede o
  propone otra cosa**
- **N2** comprobar que lo entregado es lo que pedí, no algo que se le parece:
  abrir la app y contrastar contra lo que dije
- **N3** elección de modelo, herramienta y hardware — *una línea; el desarrollo
  es la pieza 3*

### 2. Dónde vive tu app
- **N0** local vs internet; si cierro el portátil, ¿sigue vivo?
- **N1** pedir que se despliegue; entender la diferencia entre el sitio de
  pruebas y el real cuando me la nombran; **ejecutar sin bloquearme un comando
  que el agente me dicta**
- **N2** saber en cuál de los tres entornos estoy tocando ahora mismo, y leer la
  salida de ese comando lo justo para saber si fue bien o mal
- **N3** dominios, variables por entorno, logs del hosting, deshacer un
  despliegue; proveedores (Vercel, Railway, AWS, Azure) *en una línea, sin
  comparativa — envejece en seis meses*

### 3. Código vs datos
- **N0** el código se recrea, los datos no; hay datos escritos dentro del código
  que no deberían; los datos necesitan copia de seguridad
- **N1** preguntar "¿dónde queda guardado esto?" y entender la respuesta
  ("está en la base de datos" vs "está escrito en el código"); entender qué
  significa que la base de datos sea local o remota
- **N2** confirmar cuál de las dos estoy usando, y que la copia de seguridad
  existe de verdad — no que alguien dijo que existe
- **N3** migraciones, datos de prueba vs reales, restaurar un backup; tipo de
  base de datos y esquema (SQL vs NoSQL) *en una línea — para este perfil la
  decide el agente y casi siempre bien*

### 4. Secretos
- **N0** las claves no van en el código, van en un sitio aparte; una clave que
  se ve una vez ya no vuelve a ser secreta
- **N1** pedir que la clave salga del código; entender qué es el fichero de
  secretos y por qué no se sube al repositorio; saber de dónde saco una clave
  cuando me la piden; distinguir clave de servidor de clave pública de cliente
- **N2** mirar si la clave acabó en el repositorio o viaja al navegador
- **N3** rotar una clave filtrada, gestor de secretos (Bitwarden, 1Password, el
  del hosting), secretos por entorno

No hace falta saber leer un `.env`. Basta saber que existe y que ahí van.

### 5. Quién puede entrar
- **N0** tener login no es estar protegido
- **N1** preguntar "¿esto lo puede llamar cualquiera?" y entender la respuesta;
  vocabulario mínimo: autenticación es quién eres, autorización es qué puedes
  tocar
- **N2** comprobarlo yo: entrar como un usuario y verificar que no veo los datos
  de otro
- **N3** roles y permisos, RLS, tokens, revisar la superficie expuesta

### 6. Qué te puede costar
- **N0** esto genera factura y por defecto no hay tope
- **N1** entender la factura: modelo/API por uso, hosting, base de datos,
  almacenamiento, tráfico; coste fijo vs coste por uso; CPU y GPU no cuestan
  igual; pedir un tope
- **N2** mirar el consumo real y contrastarlo con lo que esperaba
- **N3** alertas, límites propios, protección anti-bots, elegir arquitectura por
  coste

### 7. Poder volver atrás
- **N0** existe forma de recuperar la versión de ayer y no es Ctrl+Z
- **N1** pedir un punto de guardado antes de un cambio grande, y pedir volver
- **N2** mirar el historial y confirmar que el punto al que quiero volver existe
  de verdad
- **N3** ramas, etiquetas, pull requests, leer un diff, conflictos

Awareness puro en N0: el agente ya hace commits solo. Lo que falta es que el
usuario sepa que el rescate existe y se pueda pedir.

### 8. Saber si funciona
- **N0** "funciona" lo decides tú probándolo, no el agente diciéndolo
- **N1** reportar con precisión (qué hice, qué esperaba, qué salió); entender qué
  te dicen cuando hablan de frontend o backend; saber que tiene que haber tests
- **N2** ejecutar los tests y ver si pasan; saber dónde mirar el error según sea
  navegador o servidor
- **N3** qué tipo de test para qué riesgo

Probar es *menos* técnico que saber que hay tests: por eso probar es N0 y los
tests son N1. **Frontend vs backend** no es bloque propio: es el vocabulario
mínimo de N1, porque sin él no se entiende ninguna respuesta sobre dónde falla
algo.

Argumento del testing: sin tests, toda la verificación recae en probar la app
final y adivinar qué pasó por el medio. Enlaza con el punto 2 de
`how-much-should-you-still-know`: delegar la validación a algo determinista.

### 9. Que siga funcionando dentro de seis meses
- **N0** cuando el proyecto crece desordenado y sin nada escrito, **el agente
  empieza a fallar más** — ese es el argumento, no la pureza arquitectónica
- **N1** pedir que documente; entender la diferencia entre documentación para
  personas e instrucciones para el agente (`CLAUDE.md`, `AGENTS.md`)
- **N2** leer el resumen del proyecto y detectar que ya no describe lo que la
  app hace
- **N3** qué va en instrucciones permanentes y qué en la conversación; cómo se
  parte el proyecto

Cierra el círculo con el final de `how-much-should-you-still-know` (la
documentación que solo leen las máquinas).

## Secciones fuera de la tabla

- **Diseño.** No encaja en una escala de riesgo: es criterio, no seguridad.
  Sección propia — *lo funcional lo acierta el agente, el gusto sigue siendo
  tuyo*.
- **Cuánto delegar.** Es la bisagra del cierre, no un bloque. Plantea la
  variable y los dos fallos simétricos (el de cero delega por encima de su
  nivel, el técnico por debajo) y deja la resolución a las piezas 2 y 3.
- **Demo vs producción.** No es un bloque: es el marco entero, materializado en
  las dos líneas de flotación y en la Tabla A.

## Fronteras con las piezas 2 y 3

Cuatro temas aparecen en el core y son además el material de las rampas. Dónde
para el core:

| Tema | En el core | En la rampa |
|---|---|---|
| Miedo a la terminal | solo el hecho funcional: a veces el agente te pide ejecutar algo y hay que poder hacerlo (bloque 2, N1) | pieza 2: por qué asusta, Claude Desktop vs CLI, cómo se vence |
| No saber qué pedir | el techo existe y limita todo lo demás (bloque 1, N0) | pieza 2: cómo se sale de ahí, qué mirar para descubrir el espacio |
| Elección de modelo y herramienta | una línea diciendo que la elección existe (bloque 1, N3) | pieza 3: Codex vs Claude Code vs open source, cuál para qué |
| Cuánto delegar | se plantea la variable y los dos fallos simétricos | piezas 2 y 3: la corrección concreta de cada perfil |

Los perfiles semi-técnico (WordPress, no-code) y old school **no se mencionan en
el core** más allá de las dos secciones de anuncio. Son material de las rampas.

## Activos visuales: qué es imagen y qué es tabla

**Una sola imagen generada. Todo lo demás, tabla markdown o texto.** Cada imagen
con texto dentro necesita versión EN y ES — son dos generaciones, dos ficheros y
dos puntos de desincronización cada vez que se retoca una palabra. Ese coste
solo lo justifica el activo que se comparte fuera del artículo.

### Imagen 1 — la escalera (única imagen; hero + portada de LinkedIn)

Generada con **Codex** (modelo de imagen), que rotula texto dentro de la imagen
con fiabilidad. Dos versiones: `-en` y `-es`.

Contenido: cuatro peldaños etiquetados con los verbos — Reconocer, Conversar,
Comprobar, Decidir — y las **dos líneas de flotación** cruzando la escalera con
su rótulo ("aquí ya construyes algo que funciona" / "aquí ya puedes ponerlo
delante de gente"). En cada peldaño, **tres o cuatro etiquetas de una o dos
palabras** de los bloques que lo pueblan, con color por bloque mantenido entre
peldaños para que se vea que el mismo tema reaparece con otra exigencia.

Restricción dura: **no caben los nueve bloques × cuatro niveles**. Si se
intentan meter frases, la imagen deja de leerse en móvil y no sirve para
LinkedIn, que es lo único para lo que existe.

### Tabla A — "mismo proyecto, dos versiones" (tabla markdown, en el cuerpo)

Juguete vs productivo, dos columnas, seis filas: corre en mi portátil / vive en
internet · clave en el código / en gestor de secretos · datos en fichero local /
base de datos remota con copia · cualquiera llama la API / hay auth y límites ·
si se rompe me entero yo / hay tests y logs · nada escrito / documentación que
el agente lee.

Tabla y no imagen: dos columnas se leen bien en móvil, se traduce sin
regenerar nada y el lector puede copiarla.

### Tabla B — bloques × niveles (tabla markdown, al final)

Nueve filas × cuatro columnas, **tres a cinco palabras por celda**. Es el
resumen, no el contenido: el desarrollo de cada celda vive en el cuerpo del
artículo, un bloque por subsección con sus cuatro niveles en lista.

Restricción dura: si las celdas llevan frases completas, la tabla se sale de
ancho y es ilegible en móvil. Frases en el cuerpo, etiquetas en la tabla.

## Estructura del artículo (pieza 1)

1. Apertura: el techo — no puedes pedir lo que no sabes que existe
2. La escala: los cuatro verbos + imagen 1
3. Los nueve bloques, uno por subsección, cuatro niveles en lista
4. Las dos líneas de flotación + Tabla A (juguete vs productivo)
5. Diseño: lo funcional lo acierta el agente, el gusto es tuyo
6. Dos secciones cortas de perfil, anunciando las piezas 2 y 3
7. Cierre: cuánto delegar — la bisagra y los dos fallos simétricos
8. Tabla B como resumen final

## Base empírica y cómo se declara

La autoridad viene de tres sitios desiguales y el artículo lo dice una vez, sin
postureo:

1. **Formación a compañeros técnicos** — la mayor parte de la experiencia. Es
   material de la pieza 3, no del core.
2. **Observación de no técnicos** (amigos): la terminal asusta; no saben qué
   pedir porque no saben qué se puede hacer; quien viene de WordPress/no-code se
   adapta bien porque solo hay que rellenar huecos.
3. **Experiencia propia construyendo con agentes**: un endpoint que quedó
   abierto cuando no debía, datos hardcodeados que debían salir de base de
   datos. Detectados **probando y preguntando, no leyendo código** — que es la
   demostración del eje entero del artículo.

Regla vinculante (ver memoria `blog-article-scope`): ninguna recomendación puede
ir más allá de lo que sostiene la evidencia de arriba. Sin listas de cicatrices
de implementación propia; los dos casos entran porque *demuestran el mecanismo*,
no como anecdotario.

## Parking: material reservado para la pieza 3

No quemar en el core:

- Elección de modelo, herramienta y hardware: Codex vs Claude Code vs
  alternativas open source, cuál para qué caso.
- Gestión del harness: skills, MCP, cuándo abrir sesión nueva, cuándo compactar,
  cómo paralelizar, herramientas tipo ultracode.
- Cuánto scope dar a una tarea según modelo y herramienta; qué herramientas de
  verificación darle al agente para no tener que verificar tú.
- El patrón del perfil old school: pasos diminutos y verificación manual de
  todo, hasta que aprende a soltar.
- Arquitectura: monorepo vs microservicios y otras formas de modularidad. Un
  vibe coder sin background no toma esa decisión ni debe.

## Fuera de alcance (todas las piezas)

- Comparativa de proveedores de hosting. Envejece rápido y es otro artículo.
- Tutorial de git, de la terminal o de cualquier herramienta concreta. La serie
  enseña qué necesitas saber, no cómo se teclea.
- Cualquier recomendación de "aprende a programar de verdad". No es la tesis.

## Pendientes fuera de la serie

Anotado el 2026-08-02, a abordar **después** de publicar los artículos (ver
memoria `website-mentoring-teaching-section`):

- Sección de **mentoría** en javieraguilar.ai, con al menos dos líneas: vibe
  coding (alimentada por esta serie) y diseño de arquitectura de agentes (sin
  definir).
- Centralizar el **trabajo académico y docente** en la web. Sin investigar
  todavía: falta decidir forma y encaje en la estructura actual del sitio.
- Decidir si el post de LinkedIn de estas piezas se genera automático o se
  escribe a mano (el recopilatorio de perfiles, en concreto, pide mano).
