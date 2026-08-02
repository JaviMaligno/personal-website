# Design: "Qué necesitas saber para vibe-codear algo real" (serie de blog + activo de mentoría)

Date: 2026-08-02
Branch: `blog/vibe-coding-skills-core`
Status: approved in brainstorming (core + rampas; cuatro verbos N0–N3; nueve
bloques; dos líneas de flotación; gráfico y tabla demo/producción como activos)

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
   vengas de donde vengas. Contiene la escala N0–N3, la tabla y el gráfico.
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
  contestan.
- **N2 · Comprobar** — lo verificas tú, sin fiarte de la respuesta.
- **N3 · Decidir** — eliges entre opciones.

El verbo es lo que hace que cada nivel sea distinguible caso a caso, y filtra
solo: toda decisión técnica (modelo, proveedor, tipo de base de datos, tipo de
test, arquitectura) cae en N3 sin discusión.

## Las dos líneas de flotación

Sustituyen a la idea inicial de una sola línea demo/producción:

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
  antes de hacer
- **N2** conozco el espacio (herramientas, servicios, integraciones) y elijo en
  vez de aceptar lo primero
- **N3** elección de modelo, herramienta y hardware — *solo mencionar que la
  elección existe; el desarrollo es la pieza 3*

### 2. Dónde vive tu app
- **N0** local vs internet; si cierro el portátil, ¿sigue vivo?
- **N1** pedir que se despliegue; saber que existe un sitio de pruebas separado
  del real
- **N2** distinguir local / preview / producción y saber en cuál estoy tocando;
  usar la terminal sin miedo cuando el agente pide ejecutar algo
- **N3** dominios, variables por entorno, logs del hosting, deshacer un
  despliegue; proveedores (Vercel, Railway, AWS, Azure) *en una línea, sin
  comparativa — envejece en seis meses*

Aquí vive el miedo a la terminal y por qué hay que perderlo: el modelo a veces
te pide que ejecutes tú.

### 3. Código vs datos
- **N0** el código se recrea, los datos no; hay datos escritos dentro del código
  que no deberían
- **N1** preguntar "¿dónde queda guardado esto?" y entender la respuesta
  ("está en la base de datos" vs "está en el código")
- **N2** base de datos local vs remota, saber cuál uso y que recrear el entorno
  se lleva la local; saber que hace falta backup
- **N3** migraciones, datos de prueba vs reales, restaurar un backup; tipo de
  base de datos y esquema (SQL vs NoSQL) *en una línea — para este perfil la
  decide el agente y casi siempre bien*

### 4. Secretos
- **N0** las claves no van en el código, van en un sitio aparte
- **N1** ese fichero no se sube al repo; de dónde saco una clave cuando me la
  piden
- **N2** clave de servidor vs clave pública de cliente; una clave filtrada se
  **rota**, no se borra del código
- **N3** gestor de secretos (Bitwarden, 1Password, el del hosting), secretos por
  entorno

No hace falta saber leer un `.env`. Basta saber que existe y que ahí van.

### 5. Quién puede entrar
- **N0** tener login no es estar protegido
- **N1** preguntar "¿esto lo puede llamar cualquiera?" y entender la respuesta
- **N2** autenticación vs autorización — quién eres vs qué puedes tocar;
  comprobar que un usuario no ve los datos de otro
- **N3** roles y permisos, RLS, tokens, revisar la superficie expuesta

### 6. Qué te puede costar
- **N0** esto genera factura y por defecto no hay tope
- **N1** los tipos de coste: modelo/API por uso, hosting, base de datos,
  almacenamiento, tráfico
- **N2** mirar el consumo; coste fijo vs coste por uso; CPU y GPU no cuestan
  igual
- **N3** alertas, límites propios, protección anti-bots, elegir arquitectura por
  coste

### 7. Poder volver atrás
- **N0** existe forma de recuperar la versión de ayer y no es Ctrl+Z
- **N1** pedir un punto de guardado antes de un cambio grande, y pedir volver
- **N2** ramas para probar sin romper lo que funciona; etiquetar "esta versión
  iba bien"
- **N3** pull requests, leer un diff, conflictos

Awareness puro en N0: el agente ya hace commits solo. Lo que falta es que el
usuario sepa que el rescate existe y se pueda pedir.

### 8. Saber si funciona
- **N0** "funciona" lo decides tú probándolo, no el agente diciéndolo
- **N1** reportar con precisión (qué hice, qué esperaba, qué salió) y entender
  qué te dicen cuando hablan de frontend o backend; saber que tiene que haber
  tests
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
- **N1** pedir que documente; distinguir documentación para personas de
  instrucciones para el agente (`CLAUDE.md`, `AGENTS.md`)
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
  las dos líneas de flotación y en la tabla comparativa (abajo).

## Activos visuales

1. **Gráfico de la escala** (imagen principal, candidata a portada de LinkedIn).
   Escalera de cuatro peldaños (Reconocer / Conversar / Comprobar / Decidir) con
   las **dos líneas de flotación** marcadas, y color por bloque atravesando los
   peldaños para que se vea que el mismo tema reaparece con otra exigencia. Lo
   que la tabla no comunica de un vistazo.
2. **Tabla "mismo proyecto, dos versiones"** — juguete vs productivo. Seis
   filas: corre en mi portátil / vive en internet · clave en el código / en
   gestor de secretos · datos en fichero local / base de datos remota con backup
   · cualquiera llama la API / hay auth y límites · si se rompe me entero yo /
   hay tests y logs · nada escrito / documentación que el agente lee.
   Candidata a segunda imagen.
3. **Tabla bloques × niveles** al final del artículo: el roadmap completo y el
   activo reutilizable fuera del artículo.

Las imágenes se generan con **Codex** (modelo de imagen), que rotula texto
dentro de la imagen con fiabilidad.

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
