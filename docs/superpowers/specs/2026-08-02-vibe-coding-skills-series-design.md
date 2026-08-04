# Design: "Qué necesitas saber para vibe-codear algo real" (serie de blog + activo de mentoría)

Date: 2026-08-02
Branch: `blog/vibe-coding-skills-core`
Status: sistema rehecho tras revisión del primer borrador (v2). El eje de cuatro
niveles con Verify como peldaño queda **descartado**; ver "Historial de
decisiones".

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

El sistema tiene que aguantar **fuera del artículo**: es el esqueleto de la
mentoría, no solo el índice de una pieza. Cuando artículo y sistema entren en
conflicto, gana el sistema.

## Arquitectura de la serie: un core + dos rampas

Un artículo por perfil se repetiría solo: los perfiles no difieren en el
destino, sino en el punto de partida y en el fallo característico.

1. **Pieza 1 — el core (esta).** El bucle y el mapa. Evergreen y citable; las
   otras dos piezas y la página de mentoría apuntan aquí.
2. **Pieza 2 — desde cero.** La rampa de quien no tiene background: miedo a la
   terminal, no saber qué se puede pedir, el bucle como novedad absoluta. Los
   semi-técnicos (WordPress, no-code, automatizaciones) son una variante del
   mismo perfil con menos huecos, no un perfil aparte.
3. **Pieza 3 — desde el oficio.** La rampa del técnico: ya tiene el bucle, le
   sobra desconfianza y le falta harness.

**Alcance del plan de implementación: solo la pieza 1.** Las piezas 2 y 3
tendrán su propio ciclo.

La pieza 1 incluye **dos secciones cortas de perfil** que anuncian las
siguientes piezas sin desarrollarlas.

**No habrá artículo de taxonomía de perfiles.** En su lugar, **post
recopilatorio de LinkedIn** al cierre de la serie, enlazando las tres piezas y
la mentoría. Ese post es el que convierte.

---

# El sistema

Dos partes independientes. Una es una **metodología** (cómo trabajas), la otra
es un **mapa** (qué tienes que saber que existe). Confundirlas fue el error de
la v1.

## Parte 1 — El bucle

Especificar → construir → comprobar → corregir.

No es nada nuevo: es spec / develop / test de toda la vida. Quien viene de
software o de un dominio técnico lo tiene interiorizado y no necesita que se lo
cuenten. Quien no viene de ahí **no sabe que existe**, y por defecto trata al
agente como un chat: pide, recibe, se lo cree, sigue pidiendo. Sin bucle no hay
producto, solo una conversación larga.

**El agente participa en las cuatro fases**, no en una. Ayuda a especificar,
construye, ejecuta comprobaciones y te dice qué mirar, y propone la corrección.
Lo que distingue a cada fase no es si el agente está — está siempre — sino
**qué residuo humano queda**:

- *Especificar* — la intención es tuya. El agente redacta mejor que tú lo que
  quieres, pero no sabe qué quieres.
- *Construir* — **la única fase que se delega entera.** No queda residuo.
- *Comprobar* — el agente ejecuta y reporta; queda tuyo saber **qué categorías
  hay que comprobar** y declarar que ya está.
- *Corregir* — queda tuyo decidir si se arregla, se rehace o se descarta.

De ahí que "ya no hace falta saber programar" sea cierto y a la vez trivial:
construir era una fase de cuatro, y es la única que desaparece del todo.

Consecuencia de diseño que arregla la v1: **comprobar es una fase del bucle, no
un nivel de conocimiento.** Lo que cambia con el conocimiento no es *si*
compruebas, es *qué eres capaz de comprobar*:

- comprobación **guiada** — el agente te dice qué mirar y tú miras. Barata,
  disponible desde el minuto cero, y suficiente más a menudo de lo que parece.
- comprobación **dirigida** — compruebas lo que sabes preguntar. Acoplada a tu
  nivel en esa categoría, no a un peldaño aparte.
- comprobación **con criterio** — sabes además si la comprobación es válida y
  qué no cubre.

## Parte 2 — El mapa: doce más una

Para cada categoría, tres niveles de comprensión:

- **Aware** — sé que esta categoría existe y puede fallar. No necesito saber
  cómo funciona ni cómo se llama; necesito saber que está ahí, porque es lo que
  me hace preguntar.
- **Fluent** — entiendo el vocabulario, sé formular la pregunta y sé si la
  respuesta tiene sentido. **Es el nivel al que se llega preguntándole al propio
  agente**, con paciencia y a propósito: la ruta más barata que existe y casi
  nadie la usa deliberadamente.
- **Opinionated** — tengo criterio propio para elegir entre opciones.

**Tu nivel no es un número, es un vector.** Nadie está en el mismo peldaño en
las trece: se puede ser Opinionated en accesos y Aware en costes. El perfil es
dentado, y el gráfico tiene que reflejarlo. La escalera de la v1 mentía al
sugerir que se sube entero.

**Opinionated no es opcional en abstracto.** Es opcional en las categorías donde
tu proyecto no se juega nada, y obligatorio donde sí: si cobras, en costes; si
guardas datos ajenos, en accesos y en datos personales. La v1 lo despachaba como
"el nivel que no necesitas" y eso era falso fuera de su caso concreto.

**Doce categorías de riesgo, más una de criterio.** La decimotercera —el gusto—
no comparte naturaleza con las otras doce: en las doce el fallo tiene víctima
(tú, tu bolsillo, tus usuarios), en la de criterio no hay fallo, solo ausencia.
Va aparte y se anuncia como aparte; el guiño "12 + 1" es el que ordena la
sección.

Las familias no tienen el mismo tamaño y no pasa nada. La primera tiene una sola
categoría porque es el techo de todas las demás, no un tema más.

### Familia A — El techo

**A1. Qué se puede pedir.** No puedes preguntar por un espacio cuya existencia
desconoces. Va sola: limita a las doce restantes.
- *Aware* un agente construye sistemas enteros, no solo textos
- *Fluent* describir por resultado, pedir que investigue y proponga, entender
  cuando dice que algo no se puede o propone otra ruta
- *Opinionated* qué modelo, qué herramienta, qué hardware — *una línea; el
  desarrollo es la pieza 3*

### Familia B — Dónde está y cómo lo recupero

**B1. Dónde vive tu app.**
- *Aware* "en mi portátil" y "en internet" no son lo mismo; si cierro el
  portátil, ¿sigue vivo?
- *Fluent* pedir que se despliegue, entender la diferencia entre el sitio de
  pruebas y el real, ejecutar sin bloquearme un comando que me dictan, saber en
  cuál de los entornos estoy tocando
- *Opinionated* dominios, variables por entorno, logs del hosting, deshacer un
  despliegue, proveedores *(sin comparativa: envejece en seis meses)*

Casi nadie borra datos de producción a propósito; los borra creyendo que está en
el entorno de pruebas.

**B2. Código vs datos.**
- *Aware* el código se regenera, los datos no; hay datos escritos dentro del
  código que no deberían; los datos necesitan copia
- *Fluent* preguntar dónde queda guardado esto y entender la respuesta; base de
  datos local vs remota; confirmar que la copia existe en vez de que se haya
  mencionado
- *Opinionated* migraciones, datos de prueba vs reales, restaurar, tipo de base
  de datos y esquema

**B3. Poder volver atrás.**
- *Aware* existe forma de recuperar la versión de ayer y no es Ctrl+Z
- *Fluent* pedir un punto de guardado antes de un cambio grande, pedir volver,
  mirar el historial y confirmar que ese punto existe
- *Opinionated* ramas, etiquetas, pull requests, leer un diff

El agente ya hace commits solo. Lo que falta es saber que el rescate existe.

### Familia C — Quién sale herido si falla

**C1. Secretos.**
- *Aware* las claves no van en el código; una clave vista una vez ya no es
  secreta
- *Fluent* pedir que salga del código, entender qué es el fichero de secretos y
  por qué no se sube, saber de dónde sale una clave, distinguir clave de
  servidor de clave pública de cliente, mirar si acabó en el repositorio o viaja
  al navegador
- *Opinionated* rotación, gestor de secretos, secretos por entorno

No hace falta saber leer un `.env`. Basta saber que existe.

**Refinamiento pendiente (2026-08-04), para la pieza 2:** el nivel *Fluent*
incluye distinguir **secreto de configuración**. No todo lo que va en variables
de entorno es secreto, y no toda configuración debería ir ahí: los feature flags
son el caso típico que acaba mal colocado. Saber cuáles son las variables de
entorno de tu proyecto y cuáles de ellas son realmente secretas es parte de
tener soltura aquí. No se retrofitea al artículo publicado por sí solo (ver
política de refinamientos en el spec de la página de mentoría).

**C2. Quién puede entrar.**
- *Aware* tener login no es estar protegido
- *Fluent* preguntar si esto lo puede llamar cualquiera y entender la respuesta;
  autenticación es quién eres, autorización es qué puedes tocar; entrar como un
  usuario y comprobar que no ve los datos de otro
- *Opinionated* roles y permisos, RLS, tokens, revisar la superficie expuesta

**C3. Datos de otras personas.** *(nueva en v2)*
- *Aware* si guardas datos de terceros, el daño de un fallo no lo pagas tú
- *Fluent* saber qué datos estás recogiendo y por qué, que hay obligaciones
  legales, y pedir que no se guarde lo que no hace falta
- *Opinionated* consentimiento, retención, minimización, dónde residen los datos

Es la categoría con asimetría moral: el resto te cuesta dinero o vergüenza,
esta se la cuesta a otro.

### Familia D — Qué me va a sorprender

**D1. Qué te puede costar.**
- *Aware* esto genera factura y por defecto no hay tope
- *Fluent* entender la factura (modelo y API por uso, hosting, base de datos,
  almacenamiento, tráfico), coste fijo vs por uso, CPU y GPU no cuestan igual,
  pedir un tope y mirar el consumo real
- *Opinionated* alertas, límites propios, protección anti-bots, arquitectura por
  coste

Las facturas sorpresa son más frecuentes que las brechas.

**D2. De quién dependes.** *(nueva en v2)*
- *Aware* tu app se apoya en servicios de otros que pueden subir de precio,
  cambiar o cerrar — y no es solo dinero, es infraestructura que desaparece
- *Fluent* saber qué piezas son de terceros y cuáles son tuyas, y preguntar qué
  pasa si una falla
- *Opinionated* elegir por acoplamiento, no solo por precio; plan de salida

Separada de D1 porque el fallo no es económico: es que algo que funcionaba deja
de existir.

**D3. Aguantar más de lo que probaste.** *(nueva en v2)*
- *Aware* funciona con tres usuarios y puede caerse con trescientos
- *Fluent* saber que existe la diferencia entre probar y aguantar carga, y
  preguntar qué se rompe primero
- *Opinionated* medir, dimensionar, decidir qué optimizar

### Familia E — Cómo sé que sigue bien

**E1. Tests y dónde falla.** *(la parte de "probar y reportar" vive ahora en el
bucle, no aquí)*
- *Aware* tiene que haber tests; sin ellos toda comprobación se reduce a
  clicar la app final y adivinar qué pasó por el medio
- *Fluent* entender qué te dicen cuando hablan de frontend o backend, ejecutar
  los tests y ver si pasan, saber dónde mirar el error según sea navegador o
  servidor
- *Opinionated* qué tipo de test para qué riesgo

**E2. Que siga funcionando en seis meses.**
- *Aware* si el proyecto crece desordenado y sin nada escrito, **el agente
  empieza a fallar más** — el argumento no es pureza arquitectónica, es que tu
  herramienta empeora
- *Fluent* pedir que documente, distinguir documentación para personas de
  instrucciones para el agente (`CLAUDE.md`, `AGENTS.md`), leer el resumen del
  proyecto y detectar que ya no describe lo que la app hace
- *Opinionated* qué va en instrucciones permanentes y qué en la conversación,
  cómo se parte el proyecto

Cierra el círculo con el final de `how-much-should-you-still-know`.

### La +1 — Criterio propio

**Fuera de las doce, y por eso al final.** En las doce categorías anteriores el
fallo tiene víctima. Aquí no hay fallo: hay ausencia. Nadie te dirá nunca que
está mal, porque no lo está — está bien y es anónimo.

- *Aware* lo que sale por defecto funciona y se parece a todo lo demás
- *Fluent* sé nombrar qué no me gusta con precisión suficiente para que se
  corrija
- *Opinionated* tengo una dirección propia y la sostengo

Es la única donde no tener background es una desventaja real sin atajo: en las
doce basta saber que la categoría existe para poder preguntar; aquí hay que
mirar y decidir que no te gusta, y eso no se delega ni se pregunta.

## La línea de producción: propiedad del sistema, no de la persona

Sustituye a las dos líneas de flotación de la v1, que ataban producción a un
nivel personal.

> Producción no exige que estés en un nivel. Exige que **ninguna categoría quede
> sin comprobar por nadie** — por ti, por un test, por un servicio o por otra
> persona — y que sepas cuál es cuál.

Es literalmente la tesis de
[`how-much-should-you-still-know`](../../../src/content/blog/en/how-much-should-you-still-know.md)
aplicada a quien nunca fue ingeniero: no hace falta tener el conocimiento, hace
falta tener el mecanismo. La serie se cierra sobre sí misma.

Lo que *Aware* garantiza no es que puedas comprobar; es que **sabes que la
casilla existe**, y por tanto puedes ver que está vacía. Una casilla vacía que
sabes vacía es un riesgo gestionado. Una que ignoras es el problema.

## Tesis del core

> Tu nivel no mide lo que sabes hacer. Mide **cuánto puedes soltar sin quedarte
> ciego** — y no es un número, es un mapa con huecos que puedes ver.

Los dos fallos simétricos siguen siendo la bisagra del cierre: quien viene de
cero delega por encima de su nivel (entrega lo que no puede comprobar ni sabe
que habría que comprobar); quien viene del oficio delega por debajo (se niega a
entregar lo que sí podría). Resolución en las piezas 2 y 3.

## Fronteras con las piezas 2 y 3

| Tema | En el core | En la rampa |
|---|---|---|
| Miedo a la terminal | el hecho funcional: a veces hay que ejecutar algo (B1, Fluent) | pieza 2: por qué asusta, Claude Desktop vs CLI, cómo se vence |
| No saber qué pedir | el techo existe y limita lo demás (A1, Aware) | pieza 2: cómo se sale de ahí |
| El bucle | se enuncia como metodología y por qué es novedoso | pieza 2: cómo adoptarlo sin background |
| Elección de modelo y herramienta | una línea (A1, Opinionated) | pieza 3: Codex vs Claude Code vs open source |
| Cuánto delegar | la variable y los dos fallos simétricos | piezas 2 y 3: la corrección de cada perfil |

Los perfiles semi-técnico y old school **no se mencionan en el core** fuera de
las dos secciones de anuncio.

## Activos visuales

Tres imágenes generadas con **Codex** (rotula texto con fiabilidad), cada una en
EN y ES. El criterio para imagen vs tabla es la legibilidad en móvil: una
comparativa de dos columnas o un diagrama de cuatro nodos se leen bien; una
matriz de treinta y nueve celdas no.

1. **El bucle** (hero + portada de LinkedIn). Cuatro nodos en ciclo —
   especificar, construir, comprobar, corregir — con quién hace qué en cada uno,
   y los tres alcances de la comprobación (guiada / dirigida / con criterio) como
   anotación. Es el activo más universal de la serie.
2. **El mapa dentado.** Las cinco familias con sus categorías, y la +1 aparte,, mostrando un perfil
   ejemplo desigual (fuerte en unas, Aware en otras) para que se vea de un
   vistazo que el nivel es un vector. Sin las celdas de texto — esas van en la
   tabla.
3. **Juguete vs producción.** Dos columnas enfrentadas, seis filas: corre en mi
   portátil / vive en internet · clave en el código / en gestor de secretos ·
   datos en fichero local / base de datos remota con copia · cualquiera llama la
   API / hay auth y límites · nadie comprueba esta casilla / cada casilla tiene
   quien la comprueba · nada escrito / documentación que el agente lee. `alt`
   que enumere las seis filas.

**Tabla markdown al final del artículo**: las doce categorías más la +1, por
tres niveles, tres
a cinco palabras por celda, agrupada por familia. El desarrollo va en el cuerpo.

## Estructura del artículo (pieza 1)

1. Apertura: el techo — no puedes pedir lo que no sabes que existe
2. De dónde viene esto (base empírica, un párrafo)
3. El bucle: la metodología, y por qué comprobar no es un nivel + imagen 1
4. Los tres niveles, y por qué tu nivel es un vector + imagen 2
5. Las doce categorías en cinco familias, en prosa compacta, y la +1 al cierre
   de la sección
6. La línea de producción como propiedad del sistema + imagen 3
7. Dos secciones cortas de perfil, anunciando las piezas 2 y 3
8. Cierre: cuánto delegar — los dos fallos simétricos
9. Tabla final

Nota de redacción: con trece fichas, cada una va en **prosa compacta**, no
en cuatro viñetas. Las listas largas inflan el texto y se leen peor.

## Base empírica y cómo se declara

Tres fuentes desiguales, declaradas una vez y sin postureo:

1. **Formación a compañeros técnicos** — la mayor parte de la experiencia, pero
   es material de la pieza 3.
2. **Observación de no técnicos** (amigos, muestra pequeña e informal): la
   terminal asusta; no saben qué pedir; quien viene de WordPress/no-code se
   adapta bien porque solo hay huecos que rellenar.
3. **Construir así él mismo**, incluyendo lo que ha cazado haciendo a los
   agentes.

**Encuadre obligatorio de los dos casos concretos** (endpoint abierto, valores
hardcodeados): **no son cicatrices propias de mala implementación.** Son cosas
que los agentes hacen por defecto y que él detectó — el endpoint haciendo
testing, los hardcodeados escribiéndolo en el spec por adelantado o preguntando
después ante la sospecha. Entran porque demuestran el mecanismo (se cazan usando
y preguntando, no leyendo código), nunca como anecdotario. Ver memoria
`blog-article-scope`.

Regla vinculante: ninguna recomendación puede ir más allá de lo que sostiene esa
evidencia.

## Parking: material reservado para la pieza 3

- Elección de modelo, herramienta y hardware: Codex vs Claude Code vs open
  source, cuál para qué caso.
- Gestión del harness: skills, MCP, cuándo abrir sesión nueva, cuándo compactar,
  cómo paralelizar, herramientas tipo ultracode.
- Cuánto scope dar según modelo y herramienta; qué herramientas de verificación
  darle al agente para no verificar tú.
- El patrón old school: pasos diminutos y verificación manual de todo.
- Arquitectura: monorepo vs microservicios y otras formas de modularidad.

## Fuera de alcance (todas las piezas)

- Comparativa de proveedores de hosting. Envejece rápido.
- Tutorial de git, de la terminal o de cualquier herramienta concreta.
- Cualquier recomendación de "aprende a programar de verdad". No es la tesis.

## Historial de decisiones

**v1 → v2 (2026-08-02, tras el primer borrador).** El eje era Reconocer →
Conversar → Comprobar → Decidir, con dos líneas de flotación atadas a Conversar
y Comprobar. Descartado por tres fallos:

1. **Comprobar no está por encima de Conversar.** La comprobación guiada (mirar
   lo que te dicen que mires) es más barata que formular la pregunta correcta.
   Estaban en el mismo casillero dos cosas de coste opuesto.
2. **Comprobar no era un nivel**, era una fase del bucle de trabajo. Mezclar
   "cuánto entiendes" con "qué papel juegas en el ciclo" fue el error de raíz.
3. **"Decidir es el nivel que no necesitas"** solo era cierto en el caso más
   simple. Hay contextos donde es obligatorio.

Añadido en v2: el bucle como parte 1 del sistema; el nivel como vector y no como
escalar; el agente como vía barata de subir a Fluent; la línea de producción
como propiedad del sistema; y tres categorías nuevas (datos de otras personas,
de quién dependes, aguantar carga).

## Extensiones futuras del sistema (anotado 2026-08-02, no comprometido)

Ideas surgidas al validar el sistema v2, para cuando la serie esté en marcha:

- **Automatizar en vez de pedir.** El paso siguiente al bucle: dejar de pedirle
  cada cosa al agente y montar que ocurran solas — revisión periódica de la
  documentación contra el código, vigilancia de logs buscando fallos, informes
  de actividad. Es un salto de naturaleza distinta al de los tres niveles: no es
  entender más, es dejar de ser el disparador. Encaja como material de la pieza
  3 o como cierre de la serie; decidir dónde cuando lleguemos. Conecta con el
  caso de la documentación desactualizada (categoría 12), donde la solución que
  Javi ya aplica es precisamente que la revisión la dispare algo, no él.

- **Minicurso.** El sistema (bucle + mapa 12+1 + los tres niveles) tiene forma de
  producto vendible por su cuenta, del tipo que se comercializa online. Los tres
  artículos serían el material de entrada.
- **Artículos de transición**, uno por salto de nivel:
  - *de 0 a Aware* — el catálogo de categorías que ni sabes que existen
  - *de Aware a Fluent* — cómo usar al propio agente para subir, que es la ruta
    barata que casi nadie usa a propósito
  - *de Fluent a Opinionated* — **el más flojo de los tres tal cual**, porque en
    una categoría concreta equivale a "hazte experto en ese dominio", que no es
    enseñable en un artículo. Reformulación que sí funciona: ser Opinionated
    **sobre el propio vibe coding** — formas de trabajar, decisiones de
    herramienta y método. Es un concepto distinto del resto del eje y hay que
    decidir si cabe en el mismo marco o es otra cosa.

## Pendientes fuera de la serie

Anotado el 2026-08-02, a abordar **después** de publicar los artículos (ver
memoria `website-mentoring-teaching-section`):

- Sección de **mentoría** en javieraguilar.ai: vibe coding (alimentada por esta
  serie) y diseño de arquitectura de agentes (sin definir).
- Centralizar el **trabajo académico y docente** en la web.
- Decidir si el post recopilatorio de LinkedIn se genera automático o a mano
  (pide mano).
